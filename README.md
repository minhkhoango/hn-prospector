# HN Prospector

A CLI tool to analyze Hacker News threads, identify users, and rank them based on their comments and potential contact information.

## Configuration: GitHub Token (Recommended)
Go to GitHub > Settings > Developer settings > Personal access tokens (classic), then generate a token (no scopes required). 
The script should run 10 times faster.

Then, set GITHUB_TOKEN in terminal or in .env file.
Example:
```bash
export GITHUB_TOKEN="ghp_YourTokenStringHere"
```

## Usage

Run the tool from within the project directory:
```bash
pip install .
hn-prospector
```