"""
Anti-Bot Utilities
================

This module provides utilities to help avoid bot detection when making HTTP requests.
It includes functions for generating realistic browser headers, simulating human browsing
patterns, and setting up configured request sessions.

Usage:
------
```python
import requests
from anti_bot_utils import generate_headers, setup_session, HumanBrowsingPattern

# Create a session with anti-bot protection
session = setup_session()

# Generate realistic headers
headers = generate_headers()

# Use human-like delays between requests
human = HumanBrowsingPattern()
time.sleep(human.think_time())

# Make a request that appears to be from a human browser
response = session.get('https://example.com', headers=headers)

# Wait a realistic amount of time based on content length
time.sleep(human.reading_time(len(response.text)))
```
"""

import random
import re
import time
import threading
from typing import Dict, Any, Optional

import requests
from requests.adapters import HTTPAdapter


class HumanBrowsingPattern:
    """
    Provides human-like timing patterns for browser automation.
    
    This class generates realistic delays between actions to mimic
    human browsing behavior, making automation harder to detect.
    """
    
    @staticmethod
    def think_time() -> float:
        """
        Generate a realistic 'thinking' delay between page views.
        
        Returns:
            float: Delay in seconds (typically 2-5 seconds)
        """
        # Gaussian distribution centered around 3.5 seconds (reduced from 4.5)
        delay = max(2.0, min(5.0, random.normalvariate(3.5, 0.8)))
        return delay
    
    @staticmethod
    def navigation_delay() -> float:
        """
        Generate a delay simulating the time to navigate to a new page.
        
        Returns:
            float: Delay in seconds (typically 1-3 seconds)
        """
        return 1.0 + random.random() * 2.0
    
    @staticmethod
    def reading_time(content_length: int) -> float:
        """
        Generate a realistic reading time based on content length.
        
        Args:
            content_length: Length of content to read (in characters)
            
        Returns:
            float: Delay in seconds
        """
        # Average reading speed: ~250 words per minute
        # Average word length: ~5 characters
        # So ~50 characters per second
        estimated_reading_time = content_length / 50.0
        
        # Cap maximum reading time at 10 seconds instead of 30
        return min(10.0, max(3.0, estimated_reading_time * (0.7 + random.random() * 0.6)))


def randomize_viewport_size() -> Dict[str, int]:
    """
    Generate a random realistic viewport size.
    
    Returns:
        Dict with width and height values.
    """
    # Common desktop resolutions
    resolutions = [
        {"width": 1920, "height": 1080},  # Full HD
        {"width": 1366, "height": 768},   # Laptop common
        {"width": 1536, "height": 864},   # Notebook common
        {"width": 1440, "height": 900},   # MacBook common
        {"width": 1280, "height": 720},   # HD
        {"width": 1600, "height": 900},   # HD+
        {"width": 2560, "height": 1440},  # QHD
        {"width": 3840, "height": 2160},  # 4K UHD
        {"width": 1024, "height": 768},   # XGA
        {"width": 1280, "height": 800},   # WXGA
        {"width": 1280, "height": 1024},  # SXGA
        {"width": 1920, "height": 1200},  # WUXGA
        {"width": 2560, "height": 1600},  # WQXGA
        {"width": 3440, "height": 1440},  # UWQHD
        {"width": 5120, "height": 2880},  # 5K
        {"width": 7680, "height": 4320},  # 8K UHD
    ]
    
    # Add slight variations
    chosen = random.choice(resolutions)
    width_variation = random.randint(-5, 5)
    height_variation = random.randint(-5, 5)
    
    return {
        "width": chosen["width"] + width_variation,
        "height": chosen["height"] + height_variation
    }


def generate_client_hints() -> Dict[str, str]:
    """
    Generate client hints headers used by modern browsers.
    
    Returns:
        Dict of client hints headers.
    """
    viewport = randomize_viewport_size()
    
    # Common device pixel ratios (1.0 for non-retina, 2.0 for retina, etc.)
    pixel_ratios = [1.0, 1.5, 2.0, 2.5, 3.0]
    pixel_ratio = random.choice(pixel_ratios)
    
    # Network connection types
    connection_types = ["4g", "wifi", "3g", "2g", "5g", "ethernet"]
    
    return {
        "Sec-Ch-Ua-Mobile": "?0",  # Desktop
        "Sec-Ch-Ua-Full-Version": f"{random.randint(100, 120)}.0.{random.randint(0, 9)}.{random.randint(0, 99)}",
        "Viewport-Width": str(viewport["width"]),
        "Width": str(viewport["width"]),
        "Sec-Ch-Viewport-Width": str(viewport["width"]),
        "DPR": str(pixel_ratio),
        "Sec-Ch-Dpr": str(pixel_ratio),
        "Device-Memory": f"{random.choice([4, 8, 16])}",
        "Sec-Ch-Device-Memory": f"{random.choice([4, 8, 16])}",
        "Sec-Ch-Prefers-Color-Scheme": random.choice(["light", "dark"]),
        "Sec-Ch-Ua-Arch": random.choice(["x86", "arm"]),
        "Sec-Ch-Ua-Bitness": "64",
        "Sec-Ch-Ua-Model": "",  # Empty for desktop
        "Sec-Ch-Ua-Full-Version-List": "",  # Will be filled in if needed
        "Downlink": str(random.randint(5, 50)),
        "ECT": random.choice(connection_types),
        "RTT": str(random.randint(50, 150))
    }


def generate_headers() -> Dict[str, str]:
    """
    Generate HTTP headers that mimic a real browser.

    This function creates a set of headers that mimic a regular browser.
    It includes randomly selected User-Agent strings and other browser 
    fingerprinting elements to avoid detection.

    Returns:
        Dict[str, str]: A dictionary of HTTP headers

    Example:
        >>> headers = generate_headers()
        >>> response = requests.get('https://example.com', headers=headers)
    """
    # Large collection of modern, diverse user agents
    user_agents = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.88 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.62 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.96 Safari/537.36",
        # Chrome on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.88 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.62 Safari/537.36",
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0) Gecko/20100101 Firefox/117.0",
        # Firefox on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.0; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13.6; rv:119.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13.5; rv:118.0) Gecko/20100101 Firefox/118.0",
        # Safari on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.88 Safari/537.36 Edg/118.0.5993.88",
        # Chrome on Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        # Firefox on Linux
        "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0",
        # Opera on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/90.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 OPR/89.0.0.0",
        # Opera on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/90.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 OPR/89.0.0.0",
    ]
    
    # Choose a browser family to keep headers consistent
    is_chrome = "Chrome" in (chosen_ua := random.choice(user_agents))
    is_firefox = "Firefox" in chosen_ua
    is_safari = "Safari" in chosen_ua and "Chrome" not in chosen_ua
    is_edge = "Edg/" in chosen_ua
    
    # Randomize platform
    platforms = ["Windows", "macOS", "Linux"]
    if "Windows" in chosen_ua:
        platform = "Windows"
    elif "Macintosh" in chosen_ua:
        platform = "macOS"
    else:
        platform = random.choice(platforms)
    
    # Language preferences with slight randomization
    lang_preferences = [
        "en-US,en;q=0.9",
        "en-US,en;q=0.9,fr;q=0.8",
        "en-GB,en;q=0.9",
        "en-CA,en;q=0.9,fr-CA;q=0.8",
        "en-AU,en;q=0.9",
        "en-NZ,en;q=0.9",
        "en-IE,en;q=0.9",
        "en-IN,en;q=0.9",
        "en-ZA,en;q=0.9",
        "en-PH,en;q=0.9",
        "en-SG,en;q=0.9",
        "en-HK,en;q=0.9",
        "en-MY,en;q=0.9",
        "en-NG,en;q=0.9",
        "en-GH,en;q=0.9",
        "en-KE,en;q=0.9",
        "en-TZ,en;q=0.9",
        "en-UG,en;q=0.9",
    ]
    
    # Possible referrers to make it look like we're coming from somewhere
    referrers = [
        "https://www.google.com/search?q=best+electronics",
        "https://www.google.com/search?q=latest+kindle+reviews",
        "https://www.google.com/search?q=buy+echo+dot",
        "https://www.google.com/search?q=amazon+devices+sale",
        "https://www.bing.com/search?q=top+electronics+deals",
        "https://www.bing.com/search?q=kindle+vs+nook",
        "https://www.bing.com/search?q=best+smart+speakers",
        "https://www.bing.com/search?q=amazon+device+discounts",
        "https://www.reddit.com/r/electronics/",
        "https://www.reddit.com/r/kindle/",
        "https://www.reddit.com/r/amazonecho/",
        "https://www.reddit.com/r/amazon/",
        "https://www.youtube.com/results?search_query=best+electronics+2023",
        "https://www.youtube.com/results?search_query=kindle+reviews",
        "https://www.youtube.com/results?search_query=echo+dot+setup",
        "https://www.youtube.com/results?search_query=amazon+device+unboxing",
        "https://www.amazon.com/",
        "https://www.amazon.com/s?k=electronics",
        "https://www.amazon.com/s?k=kindle",
        "https://www.amazon.com/s?k=echo+dot",
        "https://www.amazon.com/s?k=amazon+devices",
        "https://www.techradar.com/news/best-electronics",
        "https://www.cnet.com/topics/electronics/",
        "https://www.wired.com/category/gear/",
        "https://www.theverge.com/tech",
        None,  # Sometimes no referrer
    ]
    
    # Generate a browser-specific accept header
    if is_firefox:
        accept = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    elif is_safari:
        accept = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    else:  # Chrome/Edge
        accept = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    
    # Base headers that almost all browsers send
    headers = {
        "User-Agent": chosen_ua,
        "Accept-Language": random.choice(lang_preferences),
        "Accept": accept,
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Ch-Ua-Platform": f'"{platform}"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Connection": "keep-alive",
        "DNT": "1" if random.random() > 0.7 else None,  # Some users have Do Not Track enabled
    }
    
    # Add a referrer with 80% probability (sometimes users visit directly)
    referrer = random.choice(referrers)
    if referrer and random.random() < 0.8:
        headers["Referer"] = referrer
        headers["Sec-Fetch-Site"] = "cross-site" if "example.com" not in referrer else "same-origin"
    else:
        headers["Sec-Fetch-Site"] = "none"
    
    # Add browser-specific headers
    if is_chrome:
        chrome_version = re.search(r"Chrome/(\d+)", chosen_ua)
        if chrome_version:
            version = chrome_version.group(1)
            headers["Sec-Ch-Ua"] = f'"Google Chrome";v="{version}", " Not A;Brand";v="99", "Chromium";v="{version}"'
    elif is_edge:
        edge_version = re.search(r"Edg/(\d+)", chosen_ua)
        if edge_version:
            version = edge_version.group(1)
            headers["Sec-Ch-Ua"] = f'"Microsoft Edge";v="{version}", " Not A;Brand";v="99", "Chromium";v="{version}"'
    elif is_firefox:
        firefox_version = re.search(r"Firefox/(\d+)", chosen_ua)
        if firefox_version:
            version = firefox_version.group(1)
            headers["Sec-Ch-Ua"] = f'"Firefox";v="{version}", "Gecko";v="{version}"'
    elif is_safari:
        safari_version = re.search(r"Version/(\d+)", chosen_ua)
        if safari_version:
            version = safari_version.group(1)
            headers["Sec-Ch-Ua"] = f'"Safari";v="{version}", "Apple";v="{version}"'
    elif "OPR/" in chosen_ua:
        opera_version = re.search(r"OPR/(\d+)", chosen_ua)
        if opera_version:
            version = opera_version.group(1)
            headers["Sec-Ch-Ua"] = f'"Opera";v="{version}", " Not A;Brand";v="99", "Chromium";v="{version}"'
    
    # Add client hints with 70% probability (modern browsers)
    if random.random() < 0.7:
        client_hints = generate_client_hints()
        # Only add client hints compatible with the browser type
        if is_chrome or is_edge:
            # Chrome/Edge support all client hints
            headers.update(client_hints)
        elif is_firefox:
            # Firefox supports fewer client hints
            firefox_supported = ["Viewport-Width", "Width", "DPR"]
            headers.update({k: v for k, v in client_hints.items() if k in firefox_supported})
        elif is_safari:
            # Safari supports even fewer client hints
            safari_supported = ["Viewport-Width", "Width"]
            headers.update({k: v for k, v in client_hints.items() if k in safari_supported})
    
    # Sometimes add random custom cookies or headers for even more randomness
    if random.random() < 0.3:
        session_token = ''.join(random.choices('0123456789abcdef', k=32))
        headers["Cookie"] = f"session-id={session_token}; preferences=default"
    
    # Remove None values
    return {k: v for k, v in headers.items() if v is not None}


def setup_session() -> requests.Session:
    """
    Create and configure a requests Session with optimized settings for avoiding bot detection.

    This function sets up a Session object with proper connection pooling
    configuration and browser-like behavior.

    Returns:
        requests.Session: A configured Session object

    Example:
        >>> session = setup_session()
        >>> try:
        ...     response = session.get('https://example.com', headers=generate_headers())
        ... finally:
        ...     session.close()
    """
    session = requests.Session()

    # Configure connection pooling
    adapter = HTTPAdapter(
        pool_connections=10,  # Number of connection pools
        pool_maxsize=10,  # Connections per pool
        max_retries=0,  # We handle retries manually
    )

    # Mount the adapter for both HTTP and HTTPS
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set a default cookie jar that preserves cookies between requests
    session.cookies.clear()
    
    # Add initial browser-like behavior with 50% probability
    if random.random() > 0.5:
        session.cookies.set("preferences", "default")
    
    return session


def perform_request_with_anti_bot_measures(
    url: str, 
    method: str = "GET", 
    proxies: Optional[Dict[str, str]] = None, 
    timeout: int = 10,
    data: Optional[Dict[str, Any]] = None,
    add_delays: bool = True,
    fast_check: bool = False,
    session: Optional[requests.Session] = None
) -> requests.Response:
    """
    Perform an HTTP request with anti-bot measures.
    
    This is a high-level function that applies all anti-bot techniques:
    - Creates a session with appropriate settings
    - Generates realistic headers
    - Adds human-like delays before and after the request
    - Handles cookies properly
    
    Args:
        url: The URL to request
        method: HTTP method (default: "GET")
        proxies: Optional proxy configuration
        timeout: Request timeout in seconds
        data: Optional data for POST requests
        add_delays: Whether to add human-like delays (default: True)
        fast_check: If True, uses minimal delays even when add_delays is True (for proxy testing)
        session: Optional existing session to reuse (will not be closed)
        
    Returns:
        requests.Response: The response from the server
        
    Example:
        >>> session = setup_session()
        >>> try:
        ...     # First request
        ...     response1 = perform_request_with_anti_bot_measures(
        ...         "https://example.com", session=session)
        ...     # Second request using same session (cookies maintained)
        ...     response2 = perform_request_with_anti_bot_measures(
        ...         "https://example.com/products", session=session)
        ... finally:
        ...     session.close()
    """
    # Track if we created the session internally
    internal_session = False
    
    # Create a session if one wasn't provided
    if session is None:
        session = setup_session()
        internal_session = True
        
    headers = generate_headers()
    human = HumanBrowsingPattern()
    
    try:
        # Add pre-request delay to simulate human thinking
        if add_delays:
            if fast_check:
                # Use minimal delay for proxy checking
                time.sleep(0.5)
            else:
                time.sleep(human.navigation_delay())
        
        # Make the request
        if method.upper() == "GET":
            response = session.get(
                url,
                headers=headers,
                proxies=proxies,
                timeout=timeout,
                verify=True
            )
        elif method.upper() == "POST":
            response = session.post(
                url,
                headers=headers,
                proxies=proxies,
                timeout=timeout,
                data=data,
                verify=True
            )
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        # Add post-request delay based on content length
        if add_delays and not fast_check:
            time.sleep(human.reading_time(len(response.text)))
        
        return response
    
    finally:
        # Only close the session if we created it
        if internal_session:
            session.close()


def simulate_human_browsing_sequence(
    urls: list, 
    proxies: Optional[Dict[str, str]] = None,
    timeout: int = 15,
    session: Optional[requests.Session] = None
) -> Dict[str, Any]:
    """
    Simulate a natural human browsing sequence across multiple URLs.
    
    This function visits a series of URLs in sequence, maintaining cookies
    and setting proper referrers between pages, with realistic timing
    delays between requests.
    
    Args:
        urls: List of URLs to visit in sequence
        proxies: Optional proxy configuration
        timeout: Request timeout in seconds
        session: Optional existing session to reuse
        
    Returns:
        Dict with 'responses' mapping URLs to their responses and 'session' containing
        the session object that can be reused for further requests
        
    Example:
        >>> # Create a session
        >>> result = simulate_human_browsing_sequence([
        ...     "https://example.com",
        ...     "https://example.com/products"
        ... ])
        >>> # Reuse the same session for more navigation
        >>> result2 = simulate_human_browsing_sequence([
        ...     "https://example.com/products/item123"
        ... ], session=result['session'])
        >>> # Remember to close the session when completely done
        >>> result2['session'].close()
    """
    if not urls:
        return {'responses': {}, 'session': session if session else setup_session()}
    
    # Track if we created the session internally
    internal_session = False
    
    # Create a session if one wasn't provided
    if session is None:
        session = setup_session()
        internal_session = True
    
    human = HumanBrowsingPattern()
    responses = {}
    previous_url = None
    
    try:
        for i, url in enumerate(urls):
            # Generate new headers for each request
            headers = generate_headers()
            
            # Add referrer if not the first page
            if previous_url:
                headers["Referer"] = previous_url
            
            # Add thinking delay between pages
            if i > 0:
                time.sleep(human.think_time())
            
            # Use perform_request_with_anti_bot_measures with add_delays=False
            # to avoid nested delays, and reuse our session
            response = perform_request_with_anti_bot_measures(
                url,
                method="GET",
                proxies=proxies,
                timeout=timeout,
                add_delays=False,  # Disable internal delays since we handle them here
                session=session    # Reuse the same session
            )
            
            responses[url] = response
            previous_url = url
            
            # Simulate reading time based on content length
            time.sleep(human.reading_time(len(response.text)))
        
        # Return both the responses and the session for reuse
        return {'responses': responses, 'session': session}
        
    except Exception as e:
        # Close session on error only if we created it
        if internal_session:
            session.close()
        raise e


def monitor_progress(
    total_items: int,
    processed_items: int,
    start_time: float,
    description: str = "Processing items"
) -> float:
    """
    Monitor progress of a long-running operation with adaptive sleep time.
    
    This function calculates the appropriate sleep time based on the number
    of items being processed and the time elapsed so far.
    
    Args:
        total_items: Total number of items to process
        processed_items: Number of items processed so far
        start_time: Start time of the operation (from time.time())
        description: Description of the operation for logging
        
    Returns:
        float: Recommended sleep interval before next check
    """
    if total_items == 0:
        return 1.0
    
    # Calculate progress percentage
    progress_pct = (processed_items / total_items) * 100
    
    # Calculate time elapsed and estimated time remaining
    elapsed = time.time() - start_time
    
    if processed_items == 0:
        # Avoid division by zero
        sleep_interval = 1.0
    else:
        # Calculate time per item and estimate remaining time
        time_per_item = elapsed / processed_items
        items_left = total_items - processed_items
        time_remaining = time_per_item * items_left
        
        # Set sleep interval to be proportional to estimated time remaining
        # but within reasonable bounds
        sleep_interval = min(max(1.0, time_remaining / 20), 10.0)
    
    # Print progress
    print(f"{description}: {processed_items}/{total_items} ({progress_pct:.1f}%)")
    
    return sleep_interval


def check_connectivity_and_price_visibility(
    base_url: str,
    product_urls: list,
    proxy: Optional[Dict[str, str]] = None, 
    timeout: int = 10
) -> Dict[str, Any]:
    """
    Check both connectivity to a website and price visibility for products
    using a shared session to maintain cookies and headers.
    
    This function demonstrates how to reuse a session between different
    types of checks, improving efficiency and consistency.
    
    Args:
        base_url: The main website URL to check connectivity
        product_urls: List of product URLs to check for prices
        proxy: Optional proxy configuration
        timeout: Request timeout in seconds
        
    Returns:
        Dict with connectivity status and price data
        
    Example:
        >>> result = check_connectivity_and_price_visibility(
        ...     "https://example.com",
        ...     ["https://example.com/product1", "https://example.com/product2"],
        ...     proxy={"https": "http://user:pass@proxy.example:8080"}
        ... )
        >>> print(f"Connected: {result['connected']}")
        >>> for url, price in result['prices'].items():
        ...     print(f"Price for {url}: {price}")
    """
    results = {
        'connected': False,
        'prices': {},
        'errors': []
    }
    
    # Create a session we'll reuse across all requests
    session = setup_session()
    
    try:
        # First check basic connectivity with fast_check mode
        try:
            response = perform_request_with_anti_bot_measures(
                base_url,
                proxies=proxy,
                timeout=timeout,
                fast_check=True,  # Use minimal delays for connectivity check
                session=session   # Provide our session to reuse
            )
            results['connected'] = response.status_code == 200
            results['home_page_size'] = len(response.text)
        except Exception as e:
            results['connected'] = False
            results['errors'].append(f"Connectivity error: {str(e)}")
        
        # If we connected successfully, check product prices
        if results['connected']:
            # Simulate browsing the product pages with the SAME session
            browse_result = simulate_human_browsing_sequence(
                product_urls,
                proxies=proxy,
                timeout=timeout,
                session=session  # Reuse the SAME session from connectivity check
            )
            
            # Extract prices from the product pages (simplified example)
            for url, response in browse_result['responses'].items():
                # Note: In a real implementation, you would use proper HTML parsing
                # This is just a demonstration of session reuse
                if 'price' in response.text.lower():
                    results['prices'][url] = "Price found"
                else:
                    results['prices'][url] = "No price found"
    
    finally:
        # Clean up the session when we're done with all requests
        session.close()
    
    return results 