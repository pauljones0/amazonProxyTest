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

# Folder paths for proxy files
PROXY_FILES_FOLDER = "proxies/proxies"
CHECKED_PROXY_FOLDER = "proxies/passing_proxies"
BLACKLIST_FILE = "proxies/failed_proxies.txt"

# Global settings
VERBOSITY_LEVEL = 0  # Default to minimal logging (only progress and errors)

# Statistics tracking
class ProxyStats:
    def __init__(self):
        self.total_checked = 0
        self.by_protocol = {}  # Protocol -> {checked, working, failed}
        self.failure_reasons = {}  # Reason -> count
    
    def init_protocol(self, protocol):
        """Initialize stats for a specific protocol if not already present"""
        if protocol not in self.by_protocol:
            self.by_protocol[protocol] = {
                "checked": 0,
                "working": 0,
                "failed": 0
            }
    
    def add_success(self, proxy):
        """Record a successful proxy check"""
        protocol = proxy.protocol
        self.init_protocol(protocol)
        self.by_protocol[protocol]["working"] += 1
        self.by_protocol[protocol]["checked"] += 1
        self.total_checked += 1
        
    def add_failure(self, proxy, reason="unknown"):
        """Record a failed proxy check with reason"""
        protocol = proxy.protocol
        self.init_protocol(protocol)
        self.by_protocol[protocol]["failed"] += 1
        self.by_protocol[protocol]["checked"] += 1
        self.total_checked += 1
        
        # Track failure reasons
        if reason not in self.failure_reasons:
            self.failure_reasons[reason] = 0
        self.failure_reasons[reason] += 1
    
    def display_summary(self):
        """Display a summary of proxy statistics"""
        print("\n" + "="*60)
        print("PROXY CHECKING SUMMARY")
        print("="*60)
        
        # Overall statistics
        total_working = sum(stats["working"] for stats in self.by_protocol.values())
        overall_success_rate = (total_working / self.total_checked * 100) if self.total_checked > 0 else 0
        print(f"Total proxies checked: {self.total_checked}")
        print(f"Working proxies: {total_working} ({overall_success_rate:.1f}%)")
        print(f"Failed proxies: {self.total_checked - total_working} ({100 - overall_success_rate:.1f}%)")
        
        # Statistics by protocol
        print("\nResults by protocol:")
        print("-"*60)
        print(f"{'Protocol':<10} {'Checked':<10} {'Working':<10} {'Failed':<10} {'Success %':<10}")
        print("-"*60)
        
        for protocol, stats in self.by_protocol.items():
            success_rate = (stats["working"] / stats["checked"] * 100) if stats["checked"] > 0 else 0
            print(f"{protocol:<10} {stats['checked']:<10} {stats['working']:<10} {stats['failed']:<10} {success_rate:.1f}%")
        
        # Failure reasons
        if self.failure_reasons:
            print("\nFailure reasons:")
            print("-"*60)
            for reason, count in sorted(self.failure_reasons.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / (self.total_checked - total_working) * 100) if (self.total_checked - total_working) > 0 else 0
                print(f"{reason}: {count} ({percentage:.1f}%)")
        
        print("="*60)

# Create global stats instance
PROXY_STATS = ProxyStats()

class Proxy:
    def __init__(self, protocol: str, address: str) -> None:
        self.protocol = protocol
        self.address = address
        self.ip = address.split(":")[0]
        self.port = int(address.split(":")[1])
        self.link = f"{protocol}://{address}"


def log(message, level="I", verbosity=1):
    """
    Simple logging function that prints messages with a specified level prefix.
    
    Args:
        message (str): The message to be logged
        level (str, optional): The log level indicator. Defaults to "I".
            Accepted values: "I" (INFO), "W" (WARNING), "E" (ERROR)
        verbosity (int, optional): The verbosity level of the message.
            0: Always show (progress & errors)
            1: Show important info (default)
            2: Show detailed debug info
    
    Returns:
        None
    """
    # Global verbosity level - controls which messages are displayed
    # 0: Only progress and errors
    # 1: Important info (default)
    # 2: Detailed debug info
    global VERBOSITY_LEVEL
    
    # Only print if the message's verbosity level is less than or equal to the global level
    if verbosity <= VERBOSITY_LEVEL or level == "E":  # Always show errors
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
                        log(f"Testing price visibility on {website}", verbosity=2)
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
                            log(f"Price visible through proxy {proxy.link}", verbosity=2)
                            # Record successful proxy
                            PROXY_STATS.add_success(proxy)
                            return True
                        else:
                            log(f"Price not visible through proxy {proxy.link}", verbosity=2)
                            # Record failure with specific reason
                            PROXY_STATS.add_failure(proxy, "Price not visible")
                            continue  # Try next website
                    else:
                        # Not an Amazon URL, basic connectivity is enough
                        PROXY_STATS.add_success(proxy)
                        return True
                else:
                    # Record failure with status code
                    PROXY_STATS.add_failure(proxy, f"HTTP {response.status_code}")
            except Exception as e:
                log(f"Error testing proxy {proxy.link}: {str(e)}", "W", verbosity=2)
                # Record failure with exception type
                error_type = type(e).__name__
                PROXY_STATS.add_failure(proxy, error_type)
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


def download_proxy_list(protocol):
    """
    Download a proxy list for the specified protocol from predefined sources.
    Always downloads fresh proxies each time.
    
    Args:
        protocol (str): The proxy protocol to download ("http", "socks4", or "socks5")
    
    Returns:
        list: A list of proxy addresses (as strings) that were downloaded,
              or an empty list if the download failed
    """
    ensure_folders_exist()
    
    try:
        log(f"Downloading fresh {protocol} proxies from repository")
        response = requests.get(PROXY_SOURCES[protocol], timeout=30)
        if response.status_code == 200:
            data = response.text.strip("\n").split("\n")
            log(f"Downloaded {len(data)} {protocol} proxies")
            
            # Save to file, overwriting any existing file
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
    log(f"Check started! Testing {total_proxies} proxies...", verbosity=0)
    
    while not proxy_queue.empty():
        remaining = proxy_queue.qsize()
        checked = total_proxies - remaining
        progress = round((checked / total_proxies) * 100, 1) if total_proxies > 0 else 0
        log(f"Progress: {checked}/{total_proxies} ({progress}%) checked", verbosity=0)
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
    
    log(f"Found {len(checked_proxies)} working proxies out of {total_proxies} checked", verbosity=1)
    
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
            log(f"Wrote {len(proxy_list)} {protocol} proxies to {filepath}", verbosity=1)


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
    Load proxies of specified types, always downloading fresh copies.
    
    Args:
        types (list, optional): List of proxy types to load. 
                                Defaults to ["http", "socks4", "socks5"].
    
    Returns:
        list: A list of Proxy objects representing all loaded proxies
    """
    proxies = []
    ensure_folders_exist()
    
    # Always download fresh proxy lists
    for protocol in types:
        data = download_proxy_list(protocol)
        for address in data:
            if address.strip():  # Skip empty lines
                proxies.append(Proxy(protocol, address))
        
        log(f"Loaded {len(data)} {protocol} proxies")
    
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


def save_test_results(stats):
    """
    Save the test results to a JSON file for historical tracking.
    
    Args:
        stats (ProxyStats): The statistics object containing test results
    """
    import json
    from datetime import datetime
    
    # If no proxies were checked, skip results saving
    if stats.total_checked == 0:
        log("No proxies were checked, skipping results saving", "W")
        return
    
    # Create results directory if it doesn't exist
    results_dir = "results"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    
    # Format the results
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_checked": stats.total_checked,
        "total_working": sum(s["working"] for s in stats.by_protocol.values()),
        "protocols": {
            protocol: {
                "checked": data["checked"],
                "working": data["working"],
                "failed": data["failed"],
                "success_rate": (data["working"] / data["checked"] * 100) if data["checked"] > 0 else 0
            }
            for protocol, data in stats.by_protocol.items()
        },
        "failure_reasons": stats.failure_reasons
    }
    
    # Save to the latest results file
    with open(os.path.join(results_dir, "latest_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    
    # Also save to a timestamped file for history
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(os.path.join(results_dir, f"results_{timestamp}.json"), "w") as f:
        json.dump(results, f, indent=2)
    
    # Update the README with latest results
    update_readme_with_results(results)


def update_readme_with_results(results):
    """
    Update the README.md file with the latest test results.
    
    Args:
        results (dict): The test results dictionary
    """
    # If no proxies were checked, prevent division by zero
    if results['total_checked'] == 0:
        log("No proxies were checked, skipping README update", "W")
        return
        
    # Read the current README
    with open("README.md", "r") as f:
        readme_content = f.read()
    
    # Split the README into lines for processing
    readme_lines = readme_content.split('\n')
    
    # Find where to insert results - look for the Example section end
    insert_index = None
    for i, line in enumerate(readme_lines):
        if "Working proxies will be saved to" in line:
            insert_index = i + 1
            break
    
    if insert_index is None:
        # If we can't find the insertion point, append to the end
        insert_index = len(readme_lines)
    
    # Check if there's already a "Recent Results" section and remove it
    results_start_index = None
    for i, line in enumerate(readme_lines):
        if line.strip() == "## Recent Results":
            results_start_index = i
            break
    
    if results_start_index is not None:
        # Find where the results section ends (next ## or end of file)
        results_end_index = len(readme_lines)
        for i in range(results_start_index + 1, len(readme_lines)):
            if line.startswith("## "):
                results_end_index = i
                break
        
        # Remove the existing results section
        readme_lines = readme_lines[:results_start_index] + readme_lines[results_end_index:]
        
        # Adjust the insert index if needed
        if results_start_index < insert_index:
            insert_index = results_start_index
    
    # Convert timestamp to readable format
    if 'T' in results['timestamp']:
        timestamp = results['timestamp'].split('T')[0] + ' ' + results['timestamp'].split('T')[1][:8]
    else:
        timestamp = results['timestamp'][:19]
    
    # Format the results section
    results_section = [
        "",  # Empty line for spacing
        "## Recent Results",
        "",  # Empty line for spacing
        f"Last test run: {timestamp}",
        "",  # Empty line for spacing
        "### Summary",
        f"- **Total proxies checked**: {results['total_checked']}",
        f"- **Working proxies**: {results['total_working']} ({results['total_working']/results['total_checked']*100:.1f}%)",
        f"- **Failed proxies**: {results['total_checked']-results['total_working']} ({(results['total_checked']-results['total_working'])/results['total_checked']*100:.1f}%)",
        "",  # Empty line for spacing
        "### Results by Protocol",
        "| Protocol | Checked | Working | Failed | Success % |",
        "|----------|---------|---------|--------|-----------|"
    ]
    
    # Add protocol results
    for protocol, data in sorted(results["protocols"].items()):
        results_section.append(
            f"| {protocol:<8} | {data['checked']:<7} | {data['working']:<7} | {data['failed']:<6} | {data['success_rate']:.1f}% |"
        )
    
    results_section.append("")  # Empty line for spacing
    results_section.append("### Common Failure Reasons")
    
    # Add top failure reasons (limit to top 5)
    sorted_reasons = sorted(results["failure_reasons"].items(), key=lambda x: x[1], reverse=True)
    total_failures = results['total_checked'] - results['total_working']
    
    for reason, count in sorted_reasons[:5]:
        percentage = (count / total_failures * 100) if total_failures > 0 else 0
        results_section.append(f"- {reason}: {percentage:.1f}%")
    
    # Insert the results section at the appropriate position
    updated_readme_lines = readme_lines[:insert_index] + results_section
    
    # Write the updated README
    with open("README.md", "w") as f:
        f.write('\n'.join(updated_readme_lines))


def main(workers: int, types=["http", "socks4", "socks5"], verbosity=0):
    """
    Main function that orchestrates the proxy testing process.
    
    Args:
        workers (int): Number of concurrent worker threads to use for testing proxies
        types (list, optional): List of proxy types to check. 
                                Defaults to ["http", "socks4", "socks5"].
        verbosity (int, optional): Logging verbosity level. Defaults to 0 (minimal).
    
    Returns:
        None
    
    Note:
        This function coordinates the entire proxy checking workflow by calling
        specialized functions for each step of the process.
    """
    # Set global verbosity level
    global VERBOSITY_LEVEL
    VERBOSITY_LEVEL = verbosity
    
    log(f"Worker number: {workers}")
    log(f"Check timeout: {CHECK_TIMEOUT_SECONDS}s")
    log(f"Test websites: {[site for site in TEST_WEBSITES if not site.startswith('PLACEHOLDER')]}")
    
    if not check_socks():
        log("Missing dependencies for SOCKS support. Please run `pip install pysocks`.", "W")
        if input("Go on without socks proxies check?(y/N): ") != "y":
            exit(1)
    
    log("Loading proxies", verbosity=1)
    proxies = load_proxies(types=types)
    
    if not proxies:
        log("No proxies loaded. Exiting.", "E")
        return
    
    # Load blacklisted proxies
    blacklist = load_blacklist()
    
    # Filter out blacklisted proxies
    proxies, skipped_count = filter_blacklisted_proxies(proxies, blacklist)
    log(f"Skipped {skipped_count} blacklisted proxies", verbosity=1)
    
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
    
    # Display statistical summary
    PROXY_STATS.display_summary()
    
    # Save test results
    save_test_results(PROXY_STATS)
    
    log("All done!", verbosity=0)


if __name__ == "__main__":
    # Set default values
    workers = 32
    types = ["http", "socks4", "socks5"]
    verbosity = 0
    
    try:
        # Get values from command-line args if provided
        if len(sys.argv) > 1 and sys.argv[1].isdigit():
            workers = int(sys.argv[1])
        
        if len(sys.argv) > 2:
            types = sys.argv[2].split(',')
            
        if len(sys.argv) > 3 and sys.argv[3].isdigit():
            verbosity = int(sys.argv[3])
        
        # If no command-line args for workers, prompt for it
        if len(sys.argv) <= 1:
            workers_input = input("Please enter the number of workers: (defaults to 32) ")
            if workers_input and workers_input.isdigit():
                workers = int(workers_input)
            
            # Get proxy types
            types_input = input("Proxy types to check (defaults to all: http,socks4,socks5): ")
            if types_input:
                types = types_input.split(',')
            
            # Get verbosity level
            verbosity_input = input("Verbosity level (0=minimal, 1=normal, 2=detailed) [defaults to 0]: ")
            if verbosity_input and verbosity_input.isdigit():
                verbosity = int(verbosity_input)
    except EOFError:
        # Handle non-interactive environments gracefully
        log("Running in non-interactive mode with defaults", "I")
    
    # Warn if too many workers
    if workers >= 4096:
        log("It is not recommended to use more than 4096 workers.", "W")
    
    # Run the main function
    main(workers, types=types, verbosity=verbosity)