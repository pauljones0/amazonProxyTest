import threading
import queue
import requests
import time
import sys
import random
import os
from datetime import datetime
from anti_bot_utils import generate_headers, setup_session, HumanBrowsingPattern

# Increased timeout for more lenient checking
CHECK_TIMEOUT_SECONDS = 10

# Multiple test websites - these can be replaced later
TEST_WEBSITES = [
    "https://www.amazon.ca/amazon-fire-tv-stick-hd/dp/B0CQN248PX",  # Fire TV Stick
    "https://www.amazon.ca/Echo-Dot-5th-Gen/dp/B09B8V1LZ3",         # Echo Dot
    "https://www.amazon.ca/All-new-Amazon-Kindle-Paperwhite-glare-free/dp/B0CFPWLGF2",  # Kindle
    "https://www.amazon.ca/Fire-HD-8-Tablet-Black-32GB/dp/B0CVDNLYYS",  # Fire HD 8
    "https://www.amazon.ca/dp/B09BZVX3J7"  # Fire Cube
]
        

# URLs to download proxy lists from
PROXY_SOURCES = {
    "http": "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/refs/heads/main/http.txt",
    "socks4": "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/refs/heads/main/socks4.txt",
    "socks5": "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/refs/heads/main/socks5.txt"
}

# Time threshold for refreshing proxy lists (180 minutes = 3 hours)
REFRESH_THRESHOLD_MINUTES = 180

# Folder paths for proxy files
PROXY_FILES_FOLDER = "proxies/proxies"
CHECKED_PROXY_FOLDER = "proxies/passing_proxies"
BLACKLIST_FILE = "proxies/failed_proxies.txt"

class Proxy:
    def __init__(self, protocol: str, address: str) -> None:
        self.protocol = protocol
        self.address = address
        self.ip = address.split(":")[0]
        self.port = int(address.split(":")[1])
        self.link = f"{protocol}://{address}"


def log(message, level="I"):
    """
    Simple logging function that prints messages with a specified level prefix.
    
    Args:
        message (str): The message to be logged
        level (str, optional): The log level indicator. Defaults to "I".
            Accepted values: "I" (INFO), "W" (WARNING), "E" (ERROR)
    
    Returns:
        None
    """
    levels = {"I": "INFO", "W": "WARNING", "E": "ERROR"}
    print(f"[{levels.get(level, 'INFO')}] {message}")


def check_socks() -> bool:
    """
    Check if the system has SOCKS proxy support by attempting a test connection.
    
    Returns:
        bool: True if SOCKS dependencies are installed, False otherwise
    
    Note:
        This function works by examining the exception message when trying to use
        a SOCKS proxy without proper dependencies.
    """
    try:
        requests.get(
            "https://httpbin.org/ip",
            proxies={"https": "socks5://justatest.com"},
            timeout=CHECK_TIMEOUT_SECONDS,
        )
    except Exception as e:
        return e.args[0] != "Missing dependencies for SOCKS support."
    return True


def check_proxy(proxy: Proxy) -> bool:
    """
    Test if a proxy is working by attempting to connect to test websites through it.
    Uses anti-bot measures to avoid detection and verifies price visibility on Amazon.
    
    Args:
        proxy (Proxy): The proxy object to test
    
    Returns:
        bool: True if the proxy works with at least one test website and shows prices, False otherwise
    """
    session = setup_session()
    
    try:
        # Try each test website, if any works fully, return True
        for website in TEST_WEBSITES:
            if website.startswith("PLACEHOLDER"):
                continue  # Skip placeholder URLs
            
            try:
                # Generate fresh headers for each attempt
                headers = generate_headers()
                
                # First check - Basic connectivity (200 status)
                response = session.get(
                    website,
                    headers=headers,
                    proxies={
                        "https": proxy.link,
                        "http": proxy.link,
                        "socks4": proxy.link,
                        "socks5": proxy.link,
                    },
                    timeout=CHECK_TIMEOUT_SECONDS,
                )
                
                # If basic connectivity test passes
                if response.status_code == 200:
                    # For Amazon URLs, check price visibility
                    if "amazon" in website:
                        log(f"Testing price visibility on {website}")
                        from amazon_price_checker import check_amazon_price_visibility
                        
                        # Second check - Price visibility
                        if check_amazon_price_visibility(
                            website, 
                            session=session,
                            proxies={
                                "https": proxy.link,
                                "http": proxy.link,
                                "socks4": proxy.link,
                                "socks5": proxy.link,
                            },
                            timeout=CHECK_TIMEOUT_SECONDS
                        ):
                            log(f"Price visible through proxy {proxy.link}")
                            return True
                        else:
                            log(f"Price not visible through proxy {proxy.link}")
                            continue  # Try next website
                    else:
                        # Not an Amazon URL, basic connectivity is enough
                        return True
            except Exception as e:
                log(f"Error testing proxy {proxy.link}: {str(e)}", "W")
                continue  # Try next website if this one fails
        
        return False
    finally:
        session.close()


def check_worker(proxy_queue: queue.Queue, callback_queue: queue.Queue):
    """
    Worker thread function that tests proxies from a queue and adds working ones to a result queue.
    
    Args:
        proxy_queue (queue.Queue): Queue containing proxies to check or "EXIT" signals
        callback_queue (queue.Queue): Queue where working proxies will be added
    
    Returns:
        None
    
    Note:
        The worker terminates when it receives an "EXIT" message from the queue.
        Working proxies are added to the callback_queue for later collection.
    """
    while True:
        data = proxy_queue.get()
        if data == "EXIT":
            return
        if check_proxy(data):
            callback_queue.put(data)


def ensure_folders_exist():
    """
    Create necessary folders for storing proxy files if they don't exist.
    
    Creates the folders defined in PROXY_FILES_FOLDER and CHECKED_PROXY_FOLDER
    global variables if they don't already exist.
    
    Returns:
        None
    """
    for folder in [PROXY_FILES_FOLDER, CHECKED_PROXY_FOLDER]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            log(f"Created folder: {folder}")


def should_refresh_proxies():
    """
    Check if proxy files are older than the refresh threshold or don't exist.
    
    Returns:
        bool: True if any proxy file is missing or older than REFRESH_THRESHOLD_MINUTES,
              False if all files exist and are recent enough
    
    Note:
        This function ensures that the necessary folders exist before checking files.
        It checks all three proxy types (http, socks4, socks5) and returns True 
        if any of them need refreshing.
    """
    ensure_folders_exist()
    
    for protocol in ["http", "socks4", "socks5"]:
        filepath = os.path.join(PROXY_FILES_FOLDER, f"{protocol}.txt")
        
        # If file doesn't exist, we need to download
        if not os.path.exists(filepath):
            return True
            
        # Check file modification time
        mod_time = os.path.getmtime(filepath)
        mod_datetime = datetime.fromtimestamp(mod_time)
        current_datetime = datetime.now()
        
        # Calculate minutes elapsed since last modification
        minutes_elapsed = (current_datetime - mod_datetime).total_seconds() / 60
        
        # If any file is older than threshold, refresh all
        if minutes_elapsed > REFRESH_THRESHOLD_MINUTES:
            return True
            
    return False


def download_proxy_list(protocol):
    """
    Download a proxy list for the specified protocol from predefined sources.
    
    Args:
        protocol (str): The proxy protocol to download ("http", "socks4", or "socks5")
    
    Returns:
        list: A list of proxy addresses (as strings) that were downloaded,
              or an empty list if the download failed
    
    Note:
        The function downloads from URLs defined in the PROXY_SOURCES dictionary
        and saves the results to files in the PROXY_FILES_FOLDER directory.
    """
    ensure_folders_exist()
    
    try:
        log(f"Downloading {protocol} proxies from repository")
        response = requests.get(PROXY_SOURCES[protocol], timeout=30)
        if response.status_code == 200:
            data = response.text.strip("\n").split("\n")
            log(f"Downloaded {len(data)} {protocol} proxies")
            
            # Save to file
            filepath = os.path.join(PROXY_FILES_FOLDER, f"{protocol}.txt")
            with open(filepath, "w") as f:
                f.write(response.text)
                
            return data
        else:
            log(f"Failed to download {protocol} proxies. Status code: {response.status_code}", "E")
            return []
    except Exception as e:
        log(f"Error downloading {protocol} proxies: {str(e)}", "E")
        return []


def filter_blacklisted_proxies(proxies, blacklist):
    """
    Filter out proxies that are in the blacklist.
    
    Args:
        proxies (list): List of Proxy objects to filter
        blacklist (set): Set of blacklisted proxy URLs
    
    Returns:
        tuple: (filtered_proxies, skipped_count) containing:
            - filtered_proxies (list): List of Proxy objects not in the blacklist
            - skipped_count (int): Number of proxies that were filtered out
    """
    filtered_proxies = []
    for proxy in proxies:
        proxy_str = f"{proxy.protocol}://{proxy.address}"
        if proxy_str not in blacklist:
            filtered_proxies.append(proxy)
    
    skipped_count = len(proxies) - len(filtered_proxies)
    return filtered_proxies, skipped_count


def setup_worker_threads(proxies, workers):
    """
    Set up and start worker threads for proxy checking.
    
    Args:
        proxies (list): List of Proxy objects to check
        workers (int): Number of worker threads to create
    
    Returns:
        tuple: (proxy_queue, callback_queue, total_proxies) containing:
            - proxy_queue (queue.Queue): Queue with proxies to be checked
            - callback_queue (queue.Queue): Queue where working proxies will be added
            - total_proxies (int): Total number of proxies to be checked
    """
    # Randomize proxy order for better distribution of work
    random.shuffle(proxies)
    
    # Set up queues
    proxy_queue = queue.Queue()
    callback_queue = queue.Queue()
    
    # Add proxies to the queue
    for proxy in proxies:
        proxy_queue.put(proxy)
    
    # Start worker threads
    log("Starting workers")
    for _ in range(workers):
        threading.Thread(
            target=check_worker, args=(proxy_queue, callback_queue)
        ).start()
    
    return proxy_queue, callback_queue, len(proxies)


def monitor_progress(proxy_queue, total_proxies):
    """
    Monitor and report the progress of proxy checking.
    
    Args:
        proxy_queue (queue.Queue): Queue with proxies to be checked
        total_proxies (int): Total number of proxies being checked
    
    Returns:
        None
    """
    log(f"Check started! Testing {total_proxies} proxies...")
    
    while not proxy_queue.empty():
        remaining = proxy_queue.qsize()
        checked = total_proxies - remaining
        progress = round((checked / total_proxies) * 100, 1) if total_proxies > 0 else 0
        log(f"Progress: {checked}/{total_proxies} ({progress}%) checked")
        time.sleep(5)  # Update progress every 5 seconds


def collect_results(callback_queue, proxies, total_proxies):
    """
    Collect and process the results of proxy checking.
    
    Args:
        callback_queue (queue.Queue): Queue containing working proxies
        proxies (list): List of all Proxy objects that were checked
        total_proxies (int): Total number of proxies checked
    
    Returns:
        tuple: (checked_proxies, failed_proxies) containing:
            - checked_proxies (list): List of working Proxy objects
            - failed_proxies (list): List of failed Proxy objects
    """
    # Collect results
    checked_proxies = []
    while not callback_queue.empty():
        checked_proxies.append(callback_queue.get())
    
    log(f"Found {len(checked_proxies)} working proxies out of {total_proxies} checked")
    
    # Identify failed proxies (for blacklisting)
    checked_set = set(proxy.link for proxy in checked_proxies)
    failed_proxies = [proxy for proxy in proxies if proxy.link not in checked_set]
    
    return checked_proxies, failed_proxies


def organize_and_save_results(checked_proxies, types):
    """
    Organize working proxies by protocol and save them to files.
    
    Args:
        checked_proxies (list): List of working Proxy objects
        types (list): List of proxy types that were checked
    
    Returns:
        None
    """
    # Organize results by protocol
    results = {}
    for proxy in checked_proxies:
        if proxy.protocol in results.keys():
            results[proxy.protocol].append(proxy.address)
        else:
            results[proxy.protocol] = [proxy.address]
    
    # Write results to files
    ensure_folders_exist()
    for protocol in types:
        filepath = os.path.join(CHECKED_PROXY_FOLDER, f"{protocol}_checked.txt")
        with open(filepath, "w+") as f:
            proxy_list = results.get(protocol, [])
            f.write("\n".join(proxy_list))
            log(f"Wrote {len(proxy_list)} {protocol} proxies to {filepath}")


def cleanup_workers(proxy_queue, workers):
    """
    Send exit signals to worker threads to terminate them gracefully.
    
    Args:
        proxy_queue (queue.Queue): Queue used by worker threads
        workers (int): Number of worker threads to terminate
    
    Returns:
        None
    """
    # Signal worker threads to exit
    for _ in range(workers):
        proxy_queue.put("EXIT")


def load_proxy_files(protocol, types):
    """
    Load proxies of a specific protocol from file.
    
    Args:
        protocol (str): Proxy protocol to load ("http", "socks4", or "socks5")
        types (list): List of proxy types to load
    
    Returns:
        list: List of Proxy objects loaded from file
    """
    proxies = []
    try:
        filepath = os.path.join(PROXY_FILES_FOLDER, f"{protocol}.txt")
        log(f"Loading {protocol} proxies from file")
        with open(filepath, "r") as f:
            data = f.read().strip("\n").split("\n")
            loaded = 0
            for address in data:
                if address.strip():  # Skip empty lines
                    proxies.append(Proxy(protocol, address))
                    loaded += 1
            log(f"Loaded {loaded} {protocol} proxies")
    except FileNotFoundError:
        log(f"{protocol}.txt not found. Downloading...", "W")
        data = download_proxy_list(protocol)
        for address in data:
            if address.strip():  # Skip empty lines
                proxies.append(Proxy(protocol, address))
    
    return proxies


def load_proxies(types=["http", "socks4", "socks5"]):
    """
    Load proxies of specified types from files, downloading if necessary.
    
    Args:
        types (list, optional): List of proxy types to load. 
                                Defaults to ["http", "socks4", "socks5"].
    
    Returns:
        list: A list of Proxy objects representing all loaded proxies
    
    Note:
        This function first checks if proxy files need refreshing (based on age or existence),
        downloads fresh proxy lists if needed, then loads the proxies from the files.
        Empty lines in proxy files are skipped.
    """
    proxies = []
    ensure_folders_exist()
    
    # Check if we need to refresh the proxy files
    refresh_needed = should_refresh_proxies()
    if refresh_needed:
        log("Proxy files are outdated or missing. Downloading fresh proxy lists...")
        for protocol in types:
            download_proxy_list(protocol)
    
    # Load proxies from files
    for protocol in types:
        protocol_proxies = load_proxy_files(protocol, types)
        proxies.extend(protocol_proxies)
    
    return proxies


def load_blacklist():
    """
    Load blacklisted proxies from the blacklist file.
    
    Returns:
        set: A set of blacklisted proxy URLs in the format "{protocol}://{address}"
    
    Note:
        If the blacklist file doesn't exist, an empty one is created.
        Empty lines in the blacklist file are skipped.
    """
    ensure_folders_exist()
    blacklist = set()
    
    try:
        with open(BLACKLIST_FILE, "r") as f:
            for line in f:
                proxy = line.strip()
                if proxy:
                    blacklist.add(proxy)
        log(f"Loaded {len(blacklist)} blacklisted proxies")
    except FileNotFoundError:
        log("Blacklist file not found. Creating new blacklist.", "I")
        # Create empty blacklist file
        with open(BLACKLIST_FILE, "w") as f:
            pass
    
    return blacklist


def update_blacklist(failed_proxies):
    """
    Add failed proxies to the blacklist file.
    
    Args:
        failed_proxies (list): List of Proxy objects that failed testing
    
    Returns:
        None
    
    Note:
        This function loads the existing blacklist to avoid adding duplicates,
        then appends only new failed proxies to the blacklist file.
    """
    ensure_folders_exist()
    
    # Load existing blacklist to avoid duplicates
    current_blacklist = load_blacklist()
    new_entries = 0
    
    with open(BLACKLIST_FILE, "a") as f:
        for proxy in failed_proxies:
            proxy_str = f"{proxy.protocol}://{proxy.address}"
            if proxy_str not in current_blacklist:
                f.write(f"{proxy_str}\n")
                new_entries += 1
    
    log(f"Added {new_entries} new proxies to blacklist")


def main(workers: int, types=["http", "socks4", "socks5"]):
    """
    Main function that orchestrates the proxy testing process.
    
    Args:
        workers (int): Number of concurrent worker threads to use for testing proxies
        types (list, optional): List of proxy types to check. 
                                Defaults to ["http", "socks4", "socks5"].
    
    Returns:
        None
    
    Note:
        This function coordinates the entire proxy checking workflow by calling
        specialized functions for each step of the process.
    """
    log(f"Worker number: {workers}")
    log(f"Check timeout: {CHECK_TIMEOUT_SECONDS}s")
    log(f"Test websites: {[site for site in TEST_WEBSITES if not site.startswith('PLACEHOLDER')]}")
    
    if not check_socks():
        log("Missing dependencies for SOCKS support. Please run `pip install pysocks`.", "W")
        if input("Go on without socks proxies check?(y/N): ") != "y":
            exit(1)
    
    log("Loading proxies")
    proxies = load_proxies(types=types)
    
    if not proxies:
        log("No proxies loaded. Exiting.", "E")
        return
    
    # Load blacklisted proxies
    blacklist = load_blacklist()
    
    # Filter out blacklisted proxies
    proxies, skipped_count = filter_blacklisted_proxies(proxies, blacklist)
    log(f"Skipped {skipped_count} blacklisted proxies")
    
    if not proxies:
        log("All proxies are blacklisted. Exiting.", "E")
        return
    
    # Set up and start worker threads
    proxy_queue, callback_queue, total_proxies = setup_worker_threads(proxies, workers)
    
    # Monitor progress
    monitor_progress(proxy_queue, total_proxies)
    
    # Collect and process results
    checked_proxies, failed_proxies = collect_results(callback_queue, proxies, total_proxies)
    
    # Update blacklist with failed proxies
    update_blacklist(failed_proxies)
    
    # Organize and save results
    organize_and_save_results(checked_proxies, types)
    
    # Clean up worker threads
    cleanup_workers(proxy_queue, workers)
    
    log("All done!")


if __name__ == "__main__":
    # Get worker count
    if len(sys.argv) > 1:
        workers = sys.argv[1]
    else:
        workers = input("Worker number: (32) ")
    
    if not workers or not workers.isdigit():
        workers = 32
    else:
        workers = int(workers)
    
    if workers >= 4096:
        log("It is not recommended to use more than 4096 workers.", "W")
    
    # Get proxy types to check
    types_input = input("Proxy types to check (http,socks4,socks5): ")
    types = types_input.split(',') if types_input else ["http", "socks4", "socks5"]
    
    # Run the main function
    main(workers, types=types)