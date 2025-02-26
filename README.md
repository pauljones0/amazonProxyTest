# Amazon Proxy Tester

Tool for finding and validating proxies that can successfully browse Amazon product pages and display prices.

## Features

- Tests proxies against real Amazon product URLs
- Verifies price visibility (not just connectivity)
- Uses anti-bot measures to avoid detection
- Maintains proxy blacklist to avoid retesting bad proxies
- Multi-threaded design for fast concurrent testing

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/amazon-proxy-test.git
cd amazon-proxy-test

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
python amazon_proxy_test.py [workers]
```

- `workers`: Number of concurrent threads (default: 32)
- You'll be prompted to specify proxy types to check (http, socks4, socks5)

## How It Works

1. Downloads proxy lists from public sources
2. Tests each proxy against Amazon product pages
3. Verifies that prices are visible (passes bot protection)
4. Saves working proxies to separate files by type

## Project Structure

- `amazon_proxy_test.py`: Main script for testing proxies
- `amazon_price_checker.py`: Validates if prices are visible on Amazon
- `anti_bot_utils.py`: Utilities to avoid detection as a bot

## Requirements

- Python 3.6+
- requests
- beautifulsoup4
- PySocks (for SOCKS proxy support)

## Example

```bash
# Run with 64 worker threads
python amazon_proxy_test.py 64

# When prompted, you can specify proxy types
# Enter: http,socks4,socks5
```

Working proxies will be saved to `proxies/passing_proxies/` directory. 