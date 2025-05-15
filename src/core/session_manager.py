import time

class SessionManager:
    def __init__(self, driver=None):
        """
        Initialize session manager for managing app sessions
        
        Args:
            driver: Appium driver instance
        """
        self.driver = driver
        self.max_retries = 3
        self.retry_delay = 2  # seconds
    
    def set_driver(self, driver):
        """Set the Appium driver instance"""
        self.driver = driver
    
    def check_session(self):
        """
        Check if the session is valid without attempting restoration
        
        Returns:
            bool: True if session is valid, False otherwise
        """
        try:
            # Try a simple command to check if session is alive
            if self.driver:
                self.driver.get_window_size()
                return True
            else:
                print("Driver is not initialized")
                return False
        except Exception as e:
            print(f"Session appears to be invalid: {str(e)}")
            return False
    
    def get_page_source_with_retry(self, max_retries=None):
        """
        Get page source with retry mechanism for session failures
        
        Args:
            max_retries: Maximum number of retry attempts (default: self.max_retries)
        
        Returns:
            str: Page source XML, or None if failed
        """
        if max_retries is None:
            max_retries = self.max_retries
            
        for attempt in range(max_retries):
            try:
                # Simply check if we have a valid session
                if not self.check_session():
                    print(f"Session is not valid on attempt {attempt+1}/{max_retries}")
                    return None
                
                # Try to get page source
                source = self.driver.page_source
                if source:
                    return source
                    
                print(f"Empty page source returned on attempt {attempt+1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(self.retry_delay)
            except Exception as e:
                print(f"Error getting page source on attempt {attempt+1}/{max_retries}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(self.retry_delay)
        
        print("Failed to get page source after all retry attempts")
        return None
    
    def execute_safely(self, command_func, *args, **kwargs):
        """
        Execute a WebDriver command safely with session validation
        
        Args:
            command_func: Function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
        
        Returns:
            The result of the function call, or None if failed
        """
        # First check if we have a valid session
        if not self.check_session():
            print("Session is not valid before executing command")
            return None
        
        for attempt in range(self.max_retries):
            try:
                result = command_func(*args, **kwargs)
                return result
            except Exception as e:
                print(f"Command execution failed (attempt {attempt+1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        
        print("Failed to execute command after all retry attempts")
        return None
    
    def tap_safely(self, x, y):
        """
        Safely perform a tap at the given coordinates
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            bool: True if successful, False otherwise
        """
        def tap_command():
            from appium.webdriver.common.touch_action import TouchAction
            action = TouchAction(self.driver)
            action.tap(x=x, y=y).perform()
            time.sleep(0.5)  # Wait for tap effect
            return True
            
        return self.execute_safely(tap_command) 