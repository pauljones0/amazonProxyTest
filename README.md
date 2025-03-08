# Amazon Proxy Tester

Tool for finding and validating proxies that can successfully browse Amazon product pages and display prices. This is based off of [Proxy-Master](https://github.com/MuRongPIG/Proxy-Master), an amazing github repo that grabs Proxies and checks them, but the timeout on that is much quicker. I have a much slower timeout, but every single proxy that fails, is permanently added to a blacklist and is never checked again. This is a trade off I'm willing to make.

## Goals of this project

I made this project, as a way to find out if there were enough proxies out there to continually price check Amazon for price errors. The short answer is no. As far as I can tell Amazon has also blocked IP's coming from their AWS API gateway, so continually hammering Amazon to get their prices might be impossible (API gateway IP blocked and not enough free proxies out there and paid IP's not cheap enough). What's the next steps? IDK, but I think this is at a good place now.

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

## Recent Results

Last test run: 2025-03-08 07:21:56

### Summary
- **Total proxies checked**: 21616
- **Working proxies**: 157 (0.7%)
- **Failed proxies**: 21459 (99.3%)

### Results by Protocol
| Protocol | Checked | Working | Failed | Success % |
|----------|---------|---------|--------|-----------|
| http     | 7237    | 29      | 7208   | 0.4% |
| socks4   | 7400    | 69      | 7331   | 0.9% |
| socks5   | 6979    | 59      | 6920   | 0.8% |

### Common Failure Reasons
- ConnectionError: 35.1%
- ConnectTimeout: 31.4%
- ProxyError: 30.3%
- ReadTimeout: 1.3%
- SSLError: 0.8%