from appium import webdriver
from appium.webdriver.common.mobileby import MobileBy
import time
import json
import uuid

class AppiumPageSourceFetcher:
    def __init__(self, platform='android', device_name=None):
        """
        Initialize the Appium connection with default capabilities
        
        Args:
            platform: 'android' or 'ios'
            device_name: Name of the device/emulator (optional)
        """
        self.platform = platform.lower()
        
        # Set default device names based on platform
        if not device_name:
            if self.platform == 'android':
                device_name = 'Android Emulator'
            elif self.platform == 'ios':
                device_name = 'iPhone Simulator'
        
        # Basic capabilities
        self.capabilities = {
            'platformName': platform.capitalize(),
            'deviceName': device_name,
            'newCommandTimeout': 6000,  # Prevent Appium from ending the session after 6000 seconds of inactivity
        }
        
        # Platform-specific automation settings
        if self.platform == 'android':
            self.capabilities['automationName'] = 'UiAutomator2'
        elif self.platform == 'ios':
            self.capabilities['automationName'] = 'XCUITest'
            # Additional iOS-specific settings
            self.capabilities['platformVersion'] = '15.0'  # Default iOS version, can be overridden
            
        self.driver = None
        self.appium_url = None
        self.session_id = None
        # Add heartbeat settings
        self.last_command_time = 0
        self.session_timeout = 6000  # seconds (increased from 1200)
    
    def set_platform_version(self, version):
        """Set the platform version for iOS or Android"""
        self.capabilities['platformVersion'] = version
    
    def set_app(self, app_path=None, app_package=None, app_activity=None):
        """
        Set the app to be tested
        
        Args:
            app_path: Path to the app file (.apk or .ipa)
            app_package: Android app package (for Android)
            app_activity: Android app activity (for Android)
        """
        if app_path:
            self.capabilities['app'] = app_path
        
        # Android-specific settings
        if self.platform == 'android' and app_package and app_activity:
            self.capabilities['appPackage'] = app_package
            self.capabilities['appActivity'] = app_activity
    
    def connect(self, appium_url='http://localhost:4723'):
        """Connect to the Appium server"""
        self.appium_url = appium_url
        
        try:
            # Add unique session name to avoid conflicts
            self.session_id = str(uuid.uuid4())
            self.capabilities['sessionName'] = f'AppSession-{self.session_id}'
            
            # For Appium 2.0, do NOT add /wd/hub
            # For Appium 1.x, we might need /wd/hub
            # Let's try both if one fails
            
            try:
                # First try without /wd/hub (Appium 2.0)
                self.driver = webdriver.Remote(appium_url, self.capabilities)
                self.last_command_time = time.time()
                print("Connected to Appium server successfully")
                return True
            except Exception as e:
                if "404" in str(e) or "not found" in str(e).lower():
                    # Try with /wd/hub (Appium 1.x)
                    if not appium_url.endswith('/wd/hub'):
                        if appium_url.endswith('/'):
                            appium_url = f"{appium_url}wd/hub"
                        else:
                            appium_url = f"{appium_url}/wd/hub"
                        
                        print(f"Retrying with Appium 1.x URL format: {appium_url}")
                        self.driver = webdriver.Remote(appium_url, self.capabilities)
                        self.last_command_time = time.time()
                        print("Connected to Appium server successfully")
                        return True
                    else:
                        print(f"Failed to connect to Appium server: {str(e)}")
                        return False
                else:
                    print(f"Failed to connect to Appium server: {str(e)}")
                    return False
        except Exception as e:
            print(f"Failed to connect to Appium server: {str(e)}")
            return False
    
    def check_session(self):
        """Check if the session is still active without automatic reconnection"""
        if not self.driver:
            print("Session not initialized.")
            return False
        
        # Check if too much time has passed since the last command
        if time.time() - self.last_command_time > self.session_timeout:
            print("Session may have timed out.")
            return False
        
        # Try a simple command to test if the session is still active
        try:
            # Get session capabilities as a lightweight operation to check connection
            self.driver.capabilities
            self.last_command_time = time.time()
            return True
        except Exception as e:
            print(f"Session check failed: {str(e)}")
            return False
    
    def get_page_source(self):
        """Get the page source of the current screen"""
        # Make sure the session is active
        if not self.check_session():
            print("Failed to establish a valid session.")
            return None
        
        for attempt in range(3):  # Try up to 3 times
            try:
                # Add a small delay before getting page source
                time.sleep(0.5)
                
                page_source = self.driver.page_source
                self.last_command_time = time.time()
                return page_source
            except Exception as e:
                print(f"Failed to get page source (attempt {attempt+1}/3): {str(e)}")
                
                # Simply retry without disconnecting and reconnecting
                if attempt < 2:  # Only retry if we have attempts left
                    time.sleep(2)  # Wait before retrying
        
        print("Failed to get page source after multiple attempts")
        return None
    
    def execute_command_safely(self, command_func, *args, **kwargs):
        """Execute a WebDriver command with session recovery"""
        if not self.check_session():
            print("Failed to establish a valid session before executing command")
            return None
        
        for attempt in range(3):  # Try up to 3 times
            try:
                result = command_func(*args, **kwargs)
                self.last_command_time = time.time()
                return result
            except Exception as e:
                print(f"Command execution failed (attempt {attempt+1}/3): {str(e)}")
                
                # Simply retry without disconnecting and reconnecting
                if attempt < 2:  # Only retry if we have attempts left
                    time.sleep(2)  # Wait before retrying
        
        print("Failed to execute command after multiple attempts")
        return None
    
    def save_page_source(self, filename='page_source.xml'):
        """Save the page source to a file"""
        page_source = self.get_page_source()
        if page_source:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(page_source)
            print(f"Page source saved to {filename}")
            return True
        return False
    
    def disconnect(self):
        """Disconnect from the Appium server"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"Warning: Error during disconnect: {str(e)}")
            finally:
                self.driver = None
                print("Disconnected from Appium server") 