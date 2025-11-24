#!/usr/bin/env python3
"""
Fixed scraper for Mac M4 Pro ARM64 with manual ChromeDriver
"""

import time
import os
import platform
import subprocess
from typing import Optional, List, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

RATEMYSITE_URL = "https://www.ratemysite.xyz/"
DEFAULT_TIMEOUT = 45

class WebsiteScraper:
    def __init__(self, headless=True, timeout=DEFAULT_TIMEOUT):
        self.headless = headless
        self.timeout = timeout
        self.driver = None
        
    def _find_chromedriver_path(self):
        """Find the correct ChromeDriver path for Mac M4 Pro"""
        # Try common locations for ChromeDriver
        possible_paths = [
            "/opt/homebrew/bin/chromedriver",  # Homebrew ARM64 location
            "/usr/local/bin/chromedriver",      # Homebrew Intel location
            "/Applications/chromedriver",       # Manual installation
        ]
        
        # Check if chromedriver is in PATH
        try:
            result = subprocess.run(['which', 'chromedriver'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
        
        # Check predefined paths
        for path in possible_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path
                
        return None
        
    def _setup_driver(self):
        """Setup Chrome driver with Mac M4 Pro optimizations"""
        chrome_opts = Options()
        
        # Chrome options
        chrome_opts.add_argument("--headless=new")
        chrome_opts.add_argument("--disable-gpu")
        chrome_opts.add_argument("--no-sandbox")
        chrome_opts.add_argument("--disable-dev-shm-usage")
        chrome_opts.add_argument("--disable-extensions")
        chrome_opts.add_argument("--disable-plugins")
        chrome_opts.add_argument("--window-size=1920,1080")
        chrome_opts.add_argument("--disable-blink-features=AutomationControlled")
        chrome_opts.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Find Chrome binary
        chrome_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium"
        ]
        
        for chrome_path in chrome_paths:
            if os.path.exists(chrome_path):
                chrome_opts.binary_location = chrome_path
                break
        
        # Find ChromeDriver
        chromedriver_path = self._find_chromedriver_path()
        
        if not chromedriver_path:
            raise Exception("ChromeDriver not found. Please install with: brew install chromedriver")
        
        print(f"Using ChromeDriver at: {chromedriver_path}")
        
        try:
            service = Service(chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_opts)
            return WebDriverWait(self.driver, self.timeout)
        except Exception as e:
            raise Exception(f"Could not initialize Chrome browser: {str(e)}")

    def _find_first(self, xpaths: List[str]) -> Optional[object]:
        """Find first matching element from list of xpaths"""
        for xp in xpaths:
            try:
                el = self.driver.find_element(By.XPATH, xp)
                if el and el.is_displayed():
                    return el
            except (NoSuchElementException, StaleElementReferenceException):
                continue
        return None

    def _click_best_button(self) -> bool:
        """Try to click analysis/submit button"""
        xpaths = [
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'analy')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'rate')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'submit')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'generate')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'get report')]",
            "//button[@type='submit']",
            "//button",
            "//div[@role='button']",
        ]
        btn = self._find_first(xpaths)
        if not btn:
            return False
        try:
            if btn.is_enabled():
                try:
                    btn.click()
                except ElementClickInterceptedException:
                    self.driver.execute_script("arguments[0].click();", btn)
                return True
        except Exception:
            pass
        return False

    def _maybe_close_cookie_banner(self):
        """Close cookie banners if present"""
        candidates = [
            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'accept')]",
            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'agree')]",
            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'allow')]",
            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'ok')]",
            "//*[contains(@class,'cookie')]//button",
            "//*[@id='onetrust-accept-btn-handler']",
        ]
        try:
            btn = self._find_first(candidates)
            if btn:
                try:
                    btn.click()
                except ElementClickInterceptedException:
                    self.driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.3)
        except Exception:
            pass

    def _collect_result_text(self) -> str:
        """Extract result text from the page"""
        containers = self.driver.find_elements(
            By.XPATH,
            "//*[contains(@class,'result') or contains(@class,'report') or contains(@class,'output') or @role='article']",
        )
        texts = [c.text.strip() for c in containers if c.text and c.text.strip()]
        if texts:
            return "\n\n".join(texts).strip()

        # Fallback to body text
        try:
            body = self.driver.find_element(By.TAG_NAME, "body")
            return (body.text or "").strip()
        except Exception:
            return ""

    def _wait_for_content_growth(self, wait: WebDriverWait, min_growth: int = 80) -> None:
        """Wait for page content to grow (JS rendering)"""
        try:
            initial_len = len(self.driver.find_element(By.TAG_NAME, "body").text)
        except Exception:
            initial_len = 0

        try:
            wait.until(lambda d: len(d.find_element(By.TAG_NAME, "body").text) > initial_len + min_growth)
        except TimeoutException:
            pass

    def scrape_single_url(self, target_url: str) -> Dict[str, str]:
        """Scrape a single URL and return results"""
        result = {
            'url': target_url,
            'status': 'success',
            'content': '',
            'error': None
        }
        
        try:
            print(f"Setting up browser for {target_url}...")
            wait = self._setup_driver()
        except Exception as e:
            result['status'] = 'error'
            result['error'] = f'Failed to initialize browser: {str(e)}'
            return result
        
        try:
            print(f"Navigating to RateMySite...")
            self.driver.get(RATEMYSITE_URL)
            self._maybe_close_cookie_banner()

            # Find URL input
            input_xpaths = [
                "//input[@type='url']",
                "//input[contains(@placeholder,'https')]",
                "//input[contains(@placeholder,'http')]",
                "//input[contains(@placeholder,'Enter') or contains(@placeholder,'enter')]",
                "//input",
                "//textarea",
            ]
            
            try:
                input_el = wait.until(EC.presence_of_element_located((By.XPATH, "|".join(input_xpaths))))
            except Exception:
                input_el = self._find_first(input_xpaths)

            if not input_el:
                result['status'] = 'error'
                result['error'] = 'Could not locate input field on RateMySite'
                return result

            print(f"Entering URL: {target_url}")
            # Enter URL
            try:
                input_el.clear()
            except Exception:
                pass
            input_el.send_keys(target_url)
            time.sleep(0.3)

            print("Submitting for analysis...")
            # Submit
            clicked = self._click_best_button()
            if not clicked:
                try:
                    input_el.send_keys("\n")
                except Exception:
                    pass

            print("Waiting for results...")
            # Wait for results
            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//*[contains(@class,'result') or contains(@class,'report') or @role='article']")
                    )
                )
            except TimeoutException:
                self._wait_for_content_growth(wait, min_growth=120)

            time.sleep(1.0)  # Grace period

            # Extract content
            content = self._collect_result_text()
            result['content'] = content if content else 'Analysis completed but no detailed content found'
            print(f"Analysis complete for {target_url}")
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            print(f"Error analyzing {target_url}: {e}")
            
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None
                
        return result

    def scrape_multiple_urls(self, urls: List[str]) -> List[Dict[str, str]]:
        """Scrape multiple URLs"""
        results = []
        for url in urls:
            if url.strip():  # Only process non-empty URLs
                result = self.scrape_single_url(url.strip())
                results.append(result)
        return results