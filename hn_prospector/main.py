"""
HN Prospector: Main CLI Application

Orchestrates the process of fetching, parsing, filtering, and ranking
users from a Hacker News thread.
"""

import typer
import re
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from typing import List, Dict, Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

from . import hn_client, parser, filter, ranking
from .models import ContactInfo, RankedUser


logging.basicConfig(
    level=logging.DEBUG,  # Set the minimum level for messages to be processed
    format='%(asctime)s - %(levelname)s - %(message)s', # Define the log message format
    datefmt='%Y-%m-%d %H:%M:%S', # Define the date/time format
    filename='app.log', # Specify a filde to log to
    filemode='a' # Append to the file if it exists
)

app = typer.Typer(
    help="A CLI tool to find and rank interesting users from a Hacker News thread."
)
console = Console(stderr=True)

def _extract_thread_id(thread_input: str | None) -> Optional[str]:
    """Extracts the thread ID from a URL or a direct ID string."""
    # This case should not happen
    if not thread_input:
        console.print(
            f"The Hacker News thread ID or full URL not found."
        )
        raise typer.Exit(code=1)

    match = re.search(r"id=(\d+)", thread_input)
    if match:
        return match.group(1)
    
    # Check if the input is just digits
    if re.fullmatch(r"\d+", thread_input):
        return thread_input
    
    return None

@app.command()
def main(
    thread_input: Optional[str] = typer.Argument(
        None,
        help="The Hacker News thread ID or full URL. If not provided, you will be prompted."
    ),
    output_file: str = typer.Option(
        "hn_prospects.json",
        "--out",
        "-o",
        help="The JSON file to save results to. [default: hn_prospects.json]"
    ),
    max_workers: Optional[int] = typer.Option(
        None,
        "--workers",
        "-w",
        help="Number of concurrent workers for API calls. [default: 10]"
    )
):
    """
    Analyzes a Hacker News thread to find and rank interesting users.
    """
    console.print(f"[bold cyan]HN Prospector v1.0[/bold cyan]")

    # --- Interactive Prompt Logic ---
    if not thread_input:
        thread_input = typer.prompt("Please enter the HN Thread ID or URL")
    
    if max_workers is None:
        max_workers = typer.prompt(
            "Enter number of concurrent workers",
            type=int,
            default=1
        )

    # --- 1. Get Thread ID ---
    thread_id = _extract_thread_id(thread_input)
    if not thread_id:
        console.print(
            f"[bold red]Error:[/bold red] Invalid thread input. Please use an ID (45855933) or a full URL."
        )
        raise typer.Exit(code=1)
    
    console.print(f"Processing HN Thread ID: [bold yellow]{thread_id}[/bold yellow]")

    # Create a single, resilient session for all requests
    session = hn_client.get_session()

    # --- 2. Fetch and Confirm Thread ---
    html_content = hn_client.get_thread_html(thread_id, session)
    if not html_content:
        console.print(
            f"[bold red]Error:[/bold red] Could not fetch thread HTML. Check the ID or your connection."
        )
        raise typer.Exit(code=1)

    thread_title = hn_client.get_thread_title(html_content)
    console.print(f"Thread Title: [bold green]'{thread_title}'[/bold green]")

    try:
        if not typer.confirm("Is this the correct thread?"):
            console.print("Operation cancelled.")
            raise typer.Exit()
    except typer.Abort:
        console.print("\nOperation cancelled by user.")
        sys.exit(0)

    # --- 3. Parse All Comments (Once) ---
    console.print("Parsing all comments...")
    all_comments_by_user: Dict[str, List[str]] = parser.parse_comments_by_user(html_content)
    user_ids = list(all_comments_by_user.keys())
    logging.debug(f"List of user_ids: {user_ids}")
    console.print(f"Found [bold blue]{len(all_comments_by_user)}[/bold blue] unique commenters.", end=" ")

    # --- 4. Filter Users (Concurrently) ---
    console.print(f"Filtering users with [bold blue]{max_workers}[/bold blue] concurrent workers...")
    filtered_users: Dict[str, ContactInfo] = {}

    with Progress(console=console) as progress:
        task = progress.add_task("[cyan]Filtering...", total=len(user_ids))

        # Use ThreadPoolExecutor for concurrent I/O (network requests)
        with ThreadPoolExecutor(max_workers) as executor:
            # Submit all jobs
            future_to_uid = {
                executor.submit(filter.process_user, uid, session): uid
                for uid in user_ids
            }

            # Process result as they complete
            for future in as_completed(future_to_uid):
                uid = future_to_uid[future]
                result: Optional[ContactInfo] = future.result()
                if result:
                    filtered_users[uid] = result
                
                progress.update(task, advance=1)
    
    if not filtered_users:
        console.print("No interesting users found. Exiting.")
        raise typer.Exit()
    console.print(f"Found [bold green]{len(filtered_users)}[/bold green] interesting users.")

    # --- 5. Combine, Rank, and Sort ---
    unranked_users: List[RankedUser] = []

    for user_id, comments in all_comments_by_user.items():
        if user_id not in filtered_users:
            continue
        
        contact_info = filtered_users[user_id]
        user_profile = ranking.build_ranked_user(
                user_id=user_id,
                comments=comments,
                contact_info=contact_info
            )
        unranked_users.append(user_profile)

    final_ranked_list = ranking.sort_users(unranked_users)

    # --- 6. Output Results ---
    console.print(f"Saving results to [bold yellow]{output_file}[/bold yellow]...")
    output_data = [user.to_dict() for user in final_ranked_list]
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        console.print(f"[bold red]Error saving file:[/bold red] {e}")
        
    # Print a summary table to the console
    table = Table(title="Top 10 Interesting Users")
    table.add_column("Rank", style="cyan")
    table.add_column("Username", style="magenta")
    table.add_column("Comments", style="green")
    table.add_column("Word Count", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Contact Info", style="blue")

    for i, user in enumerate(final_ranked_list[:10]):
        contact = user.contact.github_repo or user.contact.about or "N/A"
        if len(contact) > 50:
            contact = contact[:47] + "..."
            
        table.add_row(
            str(i + 1),
            user.user_id,
            str(user.comment_count),
            str(user.total_word_count),
            user.contact.status,
            contact
        )

    console.print(table)
    console.print(f"[bold green]✓ Done![/bold green] Full results saved to [bold yellow]{output_file}[/bold yellow].")

if __name__ == "__main__":
    app()