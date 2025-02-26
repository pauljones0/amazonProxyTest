"""
Amazon Price Visibility Checker
==============================

This module provides functionality to check if a price is visible on an Amazon product page.
It includes functions for parsing prices from Amazon product pages using multiple selector patterns
to accommodate different price display formats.

This code integrates with the anti-bot utilities and proxy testing framework.
"""

import logging
import re
from typing import Optional, Dict
from bs4 import BeautifulSoup

# Import anti-bot utilities instead of duplicating code
from anti_bot_utils import generate_headers, setup_session

logger = logging.getLogger(__name__)

class AmazonPriceChecker:
    """
    Class for checking if a price is visible on an Amazon product page.
    
    This class handles parsing of Amazon product pages to determine if a
    price is visible and accessible.
    """
    
    def __init__(self):
        """Initialize the price checker with default settings."""
        # Price thresholds (in USD or other currency)
        self.min_price = 1.00
        self.max_price = 10000.00
        
        # Price selectors for different scenarios
        self.price_selectors = [
            {
                "selector": "span.a-price span.a-offscreen",
                "regex": r"\$?([\d,]+\.?\d*)",
            },  # Regular price
            {
                "selector": "span.a-price.a-text-price span.a-offscreen",
                "regex": r"\$?([\d,]+\.?\d*)",
            },  # Deal price
            {
                "selector": "span.a-price.apexPriceToPay span.a-offscreen",
                "regex": r"\$?([\d,]+\.?\d*)",
            },  # Prime price
            {
                "selector": 'span.a-price[data-a-color="price"] span.a-offscreen',
                "regex": r"\$?([\d,]+\.?\d*)",
            },  # Multi-seller price
            {
                "selector": "span#priceblock_dealprice",
                "regex": r"\$?([\d,]+\.?\d*)",
            },  # Lightning deal
            {
                "selector": "span#priceblock_businessprice",
                "regex": r"\$?([\d,]+\.?\d*)",
            },  # Business price
        ]
        
        # Patterns indicating product unavailability
        self.unavailable_patterns = [
            "currently unavailable",
            "see price in cart",
            "pricing unavailable",
            "temporarily out of stock",
        ]
    
    def _check_availability(self, soup: BeautifulSoup) -> bool:
        """
        Check if the product is available for purchase.

        Args:
            soup (BeautifulSoup): Parsed HTML of the product page

        Returns:
            bool: True if the product is available, False otherwise
        """
        page_text = soup.get_text().lower()
        return not any(pattern in page_text for pattern in self.unavailable_patterns)
    
    def _parse_price(self, soup: BeautifulSoup) -> Optional[float]:
        """
        Parse the product price from the page.

        This method attempts to find and parse the price using multiple selector
        patterns to handle different price display formats on Amazon.

        Args:
            soup (BeautifulSoup): Parsed HTML of the product page

        Returns:
            Optional[float]: The parsed price if found and valid, None otherwise
        """
        for config in self.price_selectors:
            elements = soup.select(config["selector"])
            for element in elements:
                try:
                    price_text = element.text.strip()
                    price_text = price_text.replace("$", "").replace(" ", "")

                    if match := re.search(config["regex"], price_text):
                        price_str = match.group(1).replace(",", "")
                        price = float(price_str)

                        if self.min_price <= price <= self.max_price:
                            return price
                        else:
                            logger.debug(f"Price outside valid range: ${price:.2f}")
                except Exception as e:
                    logger.debug(f"Price parsing error: {str(e)}")
                    continue

        return None
    
    def is_price_visible(self, url: str, session=None, proxies=None, timeout=10) -> bool:
        """
        Check if the price is visible on the given Amazon product page.
        
        This method first verifies that the page returns a 200 status code,
        then checks if the product price can be parsed.
        
        Args:
            url (str): The Amazon product URL to check
            session (requests.Session, optional): Session to use for requests
            proxies (dict, optional): Proxy configuration to use
            timeout (int, optional): Request timeout in seconds
            
        Returns:
            bool: True if the price is visible, False otherwise
        """
        # Use provided session or create a new one
        should_close_session = False
        if session is None:
            session = setup_session()
            should_close_session = True
        
        try:
            # First, check if the page returns a 200 status code
            headers = generate_headers()
            response = session.get(
                url,
                headers=headers,
                proxies=proxies,
                timeout=timeout,
                verify=True
            )
            
            # If request was not successful, return False immediately
            if response.status_code != 200:
                logger.debug(f"Page returned status code {response.status_code}")
                return False
            
            # Check for CAPTCHA or robot check
            if "captcha" in response.text.lower() or "robot check" in response.text.lower():
                logger.debug("CAPTCHA or robot check detected")
                return False
            
            # Parse the response and check for price
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Check product availability first
            if not self._check_availability(soup):
                logger.debug("Product is unavailable")
                return False
            
            # Parse price
            price = self._parse_price(soup)
            if price is not None:
                logger.debug(f"Price found: ${price:.2f}")
                return True
            else:
                logger.debug("Price not found")
                return False
            
        except Exception as e:
            logger.debug(f"Error checking price visibility: {str(e)}")
            return False
        
        finally:
            if should_close_session:
                session.close()


def check_amazon_price_visibility(url: str, session=None, proxies=None, timeout=10) -> bool:
    """
    Convenience function to check if price is visible on an Amazon product page.
    
    Args:
        url (str): The Amazon product URL to check
        session (requests.Session, optional): Session to use for requests
        proxies (dict, optional): Proxy configuration to use
        timeout (int, optional): Request timeout in seconds
        
    Returns:
        bool: True if the price is visible, False otherwise
    """
    checker = AmazonPriceChecker()
    return checker.is_price_visible(url, session, proxies, timeout) 