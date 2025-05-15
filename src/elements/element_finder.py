from appium.webdriver.common.mobileby import MobileBy
import re
import time

class ElementFinder:
    def __init__(self, driver):
        self.driver = driver
    
    def find_element(self, identifier):
        """Find an element by identifier with multiple strategies"""
        if not identifier or not self.driver:
            return None
        
        # Clean the identifier for more accurate matching
        clean_identifier = identifier.strip()
        
        # First, try standard element finding methods
        element = self._try_standard_element_finding(clean_identifier)
        if element:
            return element
        
        # Next, check if there's a popup and look there
        popup_state = self._check_for_popup()
        if popup_state and popup_state.get('has_popup', False):
            element = self._find_element_in_popup(clean_identifier)
            if element:
                return element
        
        # Finally, try positional tapping (as a last resort)
        return self._try_positional_tapping(clean_identifier)
    
    def _check_for_popup(self):
        """Get page source and check for popups"""
        try:
            page_source = self.driver.page_source
            # Ideally, we'd import from element_parser, but for simplicity we'll assume 
            # the popup detection is done elsewhere and this would just return a placeholder
            # In the real implementation, this would use detect_popup_state from element_parser
            return {'has_popup': False}  # Placeholder
        except Exception as e:
            print(f"Error checking for popup: {e}")
            return {'has_popup': False}
    
    def _try_standard_element_finding(self, clean_identifier):
        """Try standard element finding strategies"""
        try:
            # Try different strategies for finding elements
            strategies = [
                # By text/content-desc exact match
                (MobileBy.XPATH, f"//*[@text='{clean_identifier}' or @content-desc='{clean_identifier}' or @label='{clean_identifier}' or @value='{clean_identifier}' or @name='{clean_identifier}']"),
                
                # By text/content-desc contains
                (MobileBy.XPATH, f"//*[contains(@text, '{clean_identifier}') or contains(@content-desc, '{clean_identifier}') or contains(@label, '{clean_identifier}') or contains(@value, '{clean_identifier}') or contains(@name, '{clean_identifier}')]"),
                
                # By resource-id contains
                (MobileBy.XPATH, f"//*[contains(@resource-id, '{clean_identifier}')]"),
                
                # By accessibility ID (common for both platforms)
                (MobileBy.ACCESSIBILITY_ID, clean_identifier),
            ]
            
            for by, value in strategies:
                try:
                    # Using find_elements instead of find_element to avoid exceptions
                    elements = self.driver.find_elements(by, value)
                    if elements and len(elements) > 0:
                        # Check if any found element is displayed/enabled
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                return element
                except Exception as e:
                    # Silently continue to the next strategy
                    pass
            
            # If no exact match, try a more flexible contains match with whitespace normalization
            normalized_identifier = ' '.join(clean_identifier.split())  # Normalize whitespace
            flexible_xpath = f"//*[contains(translate(@text, '\t\n\r ', '    '), '{normalized_identifier}') or contains(translate(@content-desc, '\t\n\r ', '    '), '{normalized_identifier}') or contains(translate(@label, '\t\n\r ', '    '), '{normalized_identifier}') or contains(translate(@value, '\t\n\r ', '    '), '{normalized_identifier}') or contains(translate(@name, '\t\n\r ', '    '), '{normalized_identifier}')]"
            
            try:
                elements = self.driver.find_elements(MobileBy.XPATH, flexible_xpath)
                if elements and len(elements) > 0:
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            return element
            except Exception as e:
                # Silently continue to the next strategy
                pass
            
            return None
        except Exception as e:
            print(f"Error in standard element finding: {str(e)}")
            return None
    
    def _find_element_in_popup(self, clean_identifier):
        """Find an element inside a popup/alert/dialog"""
        try:
            # Try to find the element in the popup with various strategies
            popup_xpath_android = ".//android.app.Dialog//*"
            popup_xpath_ios = ".//*[contains(@type, 'Alert') or contains(@type, 'Dialog') or contains(@type, 'ActionSheet')]//*"
            
            # Combine Android and iOS XPath for finding elements in popups
            popup_strategies = [
                # By text/content-desc within popup (Android)
                (MobileBy.XPATH, f"{popup_xpath_android}[@text='{clean_identifier}' or @content-desc='{clean_identifier}']"),
                
                # By label/name/value within popup (iOS)
                (MobileBy.XPATH, f"{popup_xpath_ios}[@label='{clean_identifier}' or @name='{clean_identifier}' or @value='{clean_identifier}']"),
                
                # Contains text/content-desc within popup (Android)
                (MobileBy.XPATH, f"{popup_xpath_android}[contains(@text, '{clean_identifier}') or contains(@content-desc, '{clean_identifier}')]"),
                
                # Contains label/name/value within popup (iOS)
                (MobileBy.XPATH, f"{popup_xpath_ios}[contains(@label, '{clean_identifier}') or contains(@name, '{clean_identifier}') or contains(@value, '{clean_identifier}')]"),
            ]
            
            for by, value in popup_strategies:
                try:
                    elements = self.driver.find_elements(by, value)
                    if elements and len(elements) > 0:
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                return element
                except Exception:
                    # Silently continue to the next strategy
                    pass
                    
            return None
        except Exception as e:
            print(f"Error finding element in popup: {str(e)}")
            return None
    
    def _try_positional_tapping(self, clean_identifier):
        """Try to tap an element by calculating its position (last resort)"""
        try:
            # Get visible elements by position to possibly find the target
            elements_by_position = self._find_elements_by_position()
            
            # Look for elements that might match by text containing the identifier
            potential_elements = []
            for element in elements_by_position:
                # Extract all text attributes that might contain our identifier
                element_text = ''
                for attr in ['text', 'content-desc', 'label', 'name', 'value']:
                    try:
                        attr_value = element.get_attribute(attr)
                        if attr_value:
                            element_text += f" {attr_value}"
                    except:
                        pass
                
                # If the element contains our identifier, add it to potential elements
                if clean_identifier.lower() in element_text.lower():
                    potential_elements.append(element)
            
            # If we found potential elements, return the first one
            if potential_elements:
                return potential_elements[0]
            
            # If none found, create a dummy element that will tap in the center of the screen
            screen_size = self.driver.get_window_size()
            
            class DummyElement:
                def click(self):
                    # Tap in the center of the screen
                    center_x = screen_size['width'] // 2
                    center_y = screen_size['height'] // 2
                    
                    # Perform the tap using TouchAction
                    from appium.webdriver.common.touch_action import TouchAction
                    action = TouchAction(self.driver)
                    action.tap(x=center_x, y=center_y).perform()
                    time.sleep(0.5)  # Wait for tap effect
            
            print(f"Using fallback center-screen tap for '{clean_identifier}'")
            return DummyElement()
            
        except Exception as e:
            print(f"Error in positional tapping attempt: {str(e)}")
            return None
    
    def _find_elements_by_position(self, min_x=None, max_x=None, min_y=None, max_y=None):
        """Find all visible elements within certain screen coordinates"""
        try:
            # Get screen dimensions if bounds not provided
            screen_size = self.driver.get_window_size()
            screen_width = screen_size['width']
            screen_height = screen_size['height']
            
            # Set defaults if not provided
            if min_x is None: min_x = 0
            if max_x is None: max_x = screen_width
            if min_y is None: min_y = 0
            if max_y is None: max_y = screen_height
            
            # Get all potentially interactive elements
            xpath = "//*[@clickable='true' or @enabled='true']"
            all_elements = self.driver.find_elements(MobileBy.XPATH, xpath)
            
            # Filter elements by visibility and position
            visible_elements = []
            for element in all_elements:
                try:
                    if element.is_displayed():
                        # Get element location and size
                        location = element.location
                        size = element.size
                        
                        # Calculate element boundaries
                        elem_x = location['x']
                        elem_y = location['y']
                        elem_width = size['width']
                        elem_height = size['height']
                        elem_right = elem_x + elem_width
                        elem_bottom = elem_y + elem_height
                        
                        # Check if element is within our target area
                        if (elem_x >= min_x and elem_right <= max_x and
                            elem_y >= min_y and elem_bottom <= max_y):
                            visible_elements.append(element)
                except Exception:
                    # Skip elements that cause errors
                    pass
                    
            return visible_elements
        except Exception as e:
            print(f"Error finding elements by position: {str(e)}")
            return []
            
    def find_element_with_retry(self, find_func, max_retries=3, retry_delay=1):
        """Retry finding an element multiple times"""
        for attempt in range(max_retries):
            try:
                element = find_func()
                if element:
                    return element
                    
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
            except Exception as e:
                print(f"Find attempt {attempt+1}/{max_retries} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    
        return None 