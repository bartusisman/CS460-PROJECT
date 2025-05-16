from appium.webdriver.common.touch_action import TouchAction
import time
import re
from datetime import datetime
import calendar


class PickerHandler:
    """Handles interactions with iOS date and time pickers."""
    
    def __init__(self, driver, element_finder=None, session_manager=None):
        """
        Initialize with Appium driver instance and optional components.
        
        Args:
            driver: Appium WebDriver instance
            element_finder: Component for finding UI elements
            session_manager: Component for managing app session
        """
        self.driver = driver
        self.touch_action = TouchAction(driver)
        self.element_finder = element_finder
        self.session_manager = session_manager
        
        # Month names to integer mapping for comparisons
        self.MONTH2INT = {m: i for i, m in enumerate(calendar.month_name) if m}
    
    def _log_activity(self, message):
        """Log activity using session manager if available."""
        if self.session_manager:
            try:
                self.session_manager.log_activity(message)
            except:
                print(f"Picker activity: {message}")
        else:
            print(f"Picker activity: {message}")
    
    def _to_key(self, txt):
        """
        Convert a picker value to a comparable integer key.
        Works for days, months, or years uniformly.
        
        Args:
            txt: String value from picker (e.g., '15', 'April', '2024')
            
        Returns:
            int: Comparable integer value
        """
        txt = txt.strip()
        if txt.isdigit():
            return int(txt)                  # day or year
        
        # Try to match month name (full or abbreviated)
        for month_name in self.MONTH2INT:
            if month_name.lower() == txt.lower():
                return self.MONTH2INT[month_name]  # month name (April → 4, etc.)
            
        # Handle abbreviated month names
        for month_name in self.MONTH2INT:
            if month_name.lower()[:3] == txt.lower()[:3]:
                return self.MONTH2INT[month_name]
        
        return 0  # fallback
    
    def _find_picker_wheels(self):
        """Find all picker wheel elements."""
        try:
            picker_wheels = self.driver.find_elements("class name", "XCUIElementTypePickerWheel")
            self._log_activity(f"Found {len(picker_wheels)} picker wheels")
            return picker_wheels
        except Exception as e:
            self._log_activity(f"Error finding picker wheels: {e}")
            return []
    
    def _scroll_wheel(self, wheel, direction, distance_factor=1.0):
        """
        Scroll a picker wheel up or down.
        
        Args:
            wheel: The picker wheel element
            direction: 'up' to decrease value, 'down' to increase value
            distance_factor: Factor to adjust scroll distance (0.05 = micro scroll, 2.0 = large scroll)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get wheel dimensions
            size = wheel.size
            location = wheel.location
            
            # Calculate scroll coordinates
            center_x = location['x'] + size['width'] // 2
            center_y = location['y'] + size['height'] // 2
            
            # Adjust distance based on the provided factor
            base_distance = int(size['height'] * 0.2)
            adjusted_distance = int(base_distance * distance_factor)
            
            # Ensure minimum effective distance
            min_distance = max(25, int(size['height'] * 0.15))
            adjusted_distance = max(min_distance, min(adjusted_distance, int(size['height'] * 0.8)))
            
            self._log_activity(f"Scrolling {direction} with distance factor {distance_factor:.2f} (actual: {adjusted_distance}px)")
            
            if direction == 'up':
                # Scroll up (to decrease values)
                start_y = center_y
                end_y = center_y - adjusted_distance
            else:  # direction == 'down'
                # Scroll down (to increase values)
                start_y = center_y
                end_y = center_y + adjusted_distance
            
            # Calculate swipe duration based on distance
            if distance_factor < 0.1:
                duration = 100  # Quick swipe for micro-adjustments
            elif distance_factor < 0.3:
                duration = 150  # Quick swipe for small adjustments
            elif distance_factor < 0.7:
                duration = 200  # Medium swipe for moderate adjustments
            else:
                duration = 300  # Slow swipe for large adjustments
            
            self.driver.swipe(center_x, start_y, center_x, end_y, duration)
            
            # Adjust wait time based on distance
            wait_time = max(0.2, min(0.7, 0.2 + (distance_factor * 0.2)))
            time.sleep(wait_time)  # Allow UI to update
            return True
            
        except Exception as e:
            self._log_activity(f"Error scrolling wheel: {e}")
            return False
    
    def _values_match(self, current_value, target_value, value_type):
        """Check if current value matches the target value."""
        if value_type in ['day', 'year', 'hour', 'minute']:
            try:
                return int(current_value) == int(target_value)
            except (ValueError, TypeError):
                return False
        elif value_type == 'month':
            current_lower = str(current_value).lower()
            target_lower = str(target_value).lower()
            
            # Check for exact match
            if current_lower == target_lower:
                return True
                
            # Check for abbreviation match (Jan vs January)
            if len(current_lower) >= 3 and len(target_lower) >= 3:
                return current_lower[:3] == target_lower[:3]
                
            return False
        elif value_type == 'period':
            return current_value.upper() == str(target_value).upper()
        return False
    
    def select_value_fast(self, wheel, target_value, value_type=None):
        """
        Fast picker wheel selection with adaptive scrolling.
        
        Args:
            wheel: The picker wheel element
            target_value: The target value to select
            value_type: Type of value ('day', 'month', 'year', 'hour', 'minute', 'period')
            
        Returns:
            bool: True if successfully set, False otherwise
        """
        self._log_activity(f"Fast selecting {value_type} to: {target_value}")
        
        # Convert target to consistent type for comparison
        if value_type == 'month' and isinstance(target_value, str):
            target_key = self._to_key(target_value)
        else:
            try:
                target_key = int(target_value)
            except (ValueError, TypeError):
                target_key = self._to_key(str(target_value))
                
        # Set maximum attempts to prevent infinite loops
        max_attempts = 25
        attempts = 0
        
        # Keep track of previous values to detect oscillation
        previous_values = []
        
        # Flag to enable micro-adjustments when close
        using_micro_adjustment = False
        micro_adjustment_count = 0
        
        while attempts < max_attempts:
            try:
                # Get current value from the wheel
                current_value = wheel.get_attribute("value")
                if current_value:
                    current_key = self._to_key(current_value)
                    
                    # Add value to history to detect oscillation
                    previous_values.append(current_key)
                    if len(previous_values) > 5:
                        previous_values.pop(0)
                    
                    # Check if we've reached the target
                    if self._values_match(current_value, target_value, value_type):
                        self._log_activity(f"Target {value_type} value reached: {current_value}")
                        return True
                    
                    # Determine direction
                    direction_up = target_key > current_key  # Scroll UP for higher values
                        
                    # Calculate distance
                    distance = abs(target_key - current_key)
                    
                    # Check for oscillation
                    oscillation_detected = False
                    if len(previous_values) >= 4 and len(set(previous_values[-4:])) <= 2:
                        oscillation_detected = True
                        self._log_activity(f"Oscillation detected, using stronger scroll")
                    
                    # Enable micro-adjustments when very close to target
                    if distance <= 1:
                        using_micro_adjustment = True
                    
                    # Apply adaptive scrolling strategy
                    if using_micro_adjustment:
                        micro_adjustment_count += 1
                        
                        if micro_adjustment_count <= 2:
                            distance_factor = 0.5  # Moderate scroll
                        elif micro_adjustment_count <= 4:
                            distance_factor = 0.35  # Medium-small scroll
                        else:
                            distance_factor = 0.25  # Small scroll
                            
                        if micro_adjustment_count > 8:
                            # Try a full scroll to break out of potential stalemate
                            distance_factor = 0.8
                            micro_adjustment_count = 0
                    
                    elif oscillation_detected:
                        distance_factor = 0.5  # Use stronger scroll for oscillation
                    elif distance > 10:
                        distance_factor = 2.0  # Very far, use large swipes
                    elif distance > 5:
                        distance_factor = 1.5  # Far, use medium-large swipes
                    elif distance > 2:
                        distance_factor = 0.7  # Medium distance, use normal swipes
                    else:
                        distance_factor = 0.5  # Close, use moderate swipes
                    
                    # Use the correct scroll direction with adaptive distance
                    self._log_activity(f"Scrolling {'up' if direction_up else 'down'} to reach {target_value} (distance: {distance})")
                    self._scroll_wheel(wheel, 'up' if direction_up else 'down', distance_factor)
                    
                    # Wait between attempts
                    time.sleep(0.3 if using_micro_adjustment or oscillation_detected else 0.5)
                else:
                    # If we can't get the value, try alternating scroll directions
                    self._log_activity(f"Could not get current value, using fallback scroll")
                    self._scroll_wheel(wheel, 'up' if attempts % 2 == 0 else 'down', 1.0)
                    time.sleep(0.5)
            except Exception as e:
                self._log_activity(f"Error in select_value_fast: {e}")
                self._scroll_wheel(wheel, 'up' if attempts % 2 == 0 else 'down', 1.0)
                time.sleep(0.5)
                
            attempts += 1
            
        self._log_activity(f"Failed to set {value_type} wheel to {target_value} after {attempts} attempts")
        return False
    
    def pick_date(self, target_day, target_month, target_year):
        """
        Pick a date using fast selection strategy.
        
        Args:
            target_day (int or str): Day to pick
            target_month (str): Month to pick (e.g., 'April')
            target_year (int or str): Year to pick
            
        Returns:
            bool: True if date was successfully picked, False otherwise
        """
        self._log_activity(f"Attempting to pick date: {target_day} {target_month} {target_year}")
        
        # Convert targets to consistent format
        if isinstance(target_day, str):
            try:
                target_day = int(target_day)
            except ValueError:
                self._log_activity(f"Invalid day format: {target_day}")
                return False
        
        if isinstance(target_year, str):
            try:
                target_year = int(target_year)
            except ValueError:
                self._log_activity(f"Invalid year format: {target_year}")
                return False
        
        # Make sure target_month is properly capitalized
        if isinstance(target_month, str):
            target_month = target_month.title()
        
        # Find picker wheels
        picker_wheels = self._find_picker_wheels()
        if len(picker_wheels) < 3:
            self._log_activity("Not enough picker wheels found")
            return False
        
        # Standard iOS date picker order: Day, Month, Year
        day_wheel = picker_wheels[0]
        month_wheel = picker_wheels[1]
        year_wheel = picker_wheels[2]
        
        # Set year first (prevents issues with month days)
        year_set = self.select_value_fast(year_wheel, target_year, 'year')
        
        # Then set month
        month_set = self.select_value_fast(month_wheel, target_month, 'month')
        
        # Finally set day
        day_set = self.select_value_fast(day_wheel, target_day, 'day')
        
        # Did all three parts complete successfully?
        if year_set and month_set and day_set:
            self._log_activity(f"Successfully picked date: {target_day} {target_month} {target_year}")
            return True
        else:
            self._log_activity(f"Failed to pick date: {target_day} {target_month} {target_year}")
            return False
    
    def pick_time(self, target_hour, target_minute, target_period=None):
        """
        Pick a time using fast selection strategy.
        
        Args:
            target_hour (int or str): Hour to pick
            target_minute (int or str): Minute to pick
            target_period (str, optional): 'AM' or 'PM' for 12-hour format
            
        Returns:
            bool: True if time was successfully picked, False otherwise
        """
        self._log_activity(f"Attempting to pick time: {target_hour}:{target_minute} {target_period or ''}")
        
        # Convert targets to consistent format
        if isinstance(target_hour, str):
            try:
                target_hour = int(target_hour)
            except ValueError:
                self._log_activity(f"Invalid hour format: {target_hour}")
                return False
        
        if isinstance(target_minute, str):
            try:
                target_minute = int(target_minute)
            except ValueError:
                self._log_activity(f"Invalid minute format: {target_minute}")
                return False
        
        # Find picker wheels
        picker_wheels = self._find_picker_wheels()
        
        # Check if we're dealing with 12-hour format (with AM/PM) or 24-hour format
        using_period = target_period is not None
        required_wheels = 3 if using_period else 2
        
        if len(picker_wheels) < required_wheels:
            self._log_activity(f"Not enough picker wheels found for time picker (found {len(picker_wheels)}, need {required_wheels})")
            return False
        
        # Set hour
        hour_set = self.select_value_fast(picker_wheels[0], target_hour, 'hour')
        
        # Set minute
        minute_set = self.select_value_fast(picker_wheels[1], target_minute, 'minute')
        
        # Set AM/PM if needed
        period_set = True  # Default to true if not using
        if using_period and len(picker_wheels) >= 3:
            period_set = self.select_value_fast(picker_wheels[2], target_period, 'period')
        
        if hour_set and minute_set and period_set:
            self._log_activity(f"Successfully picked time: {target_hour}:{target_minute} {target_period or ''}")
            return True
        else:
            self._log_activity(f"Failed to pick time: {target_hour}:{target_minute} {target_period or ''}")
            return False
    
    def confirm_selection(self):
        """Click the confirm button after selecting a date/time."""
        self._log_activity("Attempting to confirm selection")
        
        try:
            # Try most obvious confirm buttons first
            try:
                confirm_button = self.driver.find_element("accessibility id", "Confirm")
                confirm_button.click()
                self._log_activity("Selection confirmed using 'Confirm' accessibility id")
                return True
            except Exception:
                pass
            
            # Try other common confirmation buttons
            for text in ["Done", "OK", "Save", "Apply"]:
                try:
                    button = self.driver.find_element("accessibility id", text)
                    button.click()
                    self._log_activity(f"Selection confirmed using '{text}' button")
                    return True
                except Exception:
                    pass
            
            # Last resort: check all buttons
            buttons = self.driver.find_elements("class name", "XCUIElementTypeButton")
            for button in buttons:
                try:
                    label = button.get_attribute("label") or ""
                    name = button.get_attribute("name") or ""
                    
                    if any(text.lower() in label.lower() or text.lower() in name.lower() 
                          for text in ["confirm", "done", "ok", "save", "apply"]):
                        button.click()
                        self._log_activity(f"Selection confirmed using button with label/name: {label or name}")
                        return True
                except Exception:
                    continue
            
            self._log_activity("Could not find any confirmation button")
            return False
            
        except Exception as e:
            self._log_activity(f"Error confirming selection: {e}")
            return False
    
    def cancel_selection(self):
        """Click the cancel button to exit without confirming."""
        self._log_activity("Attempting to cancel selection")
        
        try:
            # Try most obvious cancel buttons first
            try:
                cancel_button = self.driver.find_element("accessibility id", "Cancel")
                cancel_button.click()
                self._log_activity("Selection cancelled using 'Cancel' accessibility id")
                return True
            except Exception:
                pass
            
            # Check all buttons
            buttons = self.driver.find_elements("class name", "XCUIElementTypeButton")
            for button in buttons:
                try:
                    label = button.get_attribute("label") or ""
                    name = button.get_attribute("name") or ""
                    
                    if any(text.lower() in label.lower() or text.lower() in name.lower() 
                          for text in ["cancel", "back", "close"]):
                        button.click()
                        self._log_activity(f"Selection cancelled using button with label/name: {label or name}")
                        return True
                except Exception:
                    continue
            
            self._log_activity("Could not find any cancellation button")
            return False
            
        except Exception as e:
            self._log_activity(f"Error cancelling selection: {e}")
            return False
    
    def handle_scroll_picker(self, input_value, element=None, **kwargs):
        """
        Handle scrolling picker to select a date or time value.
        
        Args:
            input_value (str): Input string containing the value to pick (e.g., "15 April 2024")
            element (WebElement or str, optional): The element being interacted with
            **kwargs: Additional arguments including auto_confirm
            
        Returns:
            dict: Result of the picker operation
        """
        # Extract auto_confirm from kwargs with default False
        auto_confirm = kwargs.get('auto_confirm', False)
        
        # Use the element parameter if it contains a simpler value
        if isinstance(input_value, str) and isinstance(element, str) and element and len(element.split()) <= 5:
            self._log_activity(f"Using element value instead of input_value: {element}")
            input_value = element
        
        self._log_activity(f"Handling scroll picker with input: {input_value}, auto_confirm: {auto_confirm}")
        
        # Try to parse input as a date
        try:
            # Split the input value and parse it
            parts = input_value.strip().split()
            
            # Check if we have at least 3 parts for a date (day, month, year)
            if len(parts) >= 3:
                day = parts[0]
                month = parts[1].title()
                year = parts[2]
                
                success = self.pick_date(day, month, year)
                
                if success:
                    if auto_confirm:
                        confirm_success = self.confirm_selection()
                        return {
                            "success": confirm_success,
                            "message": f"Selected date: {day} {month} {year}",
                            "type": "date"
                        }
                    else:
                        return {
                            "success": True,
                            "message": f"Selected date: {day} {month} {year} (waiting for confirmation)",
                            "type": "date"
                        }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to select date: {day} {month} {year}",
                        "type": "date"
                    }
            
            # Check if it might be a time format (e.g., "10:30 AM")
            elif ":" in input_value:
                # Parse time format
                time_parts = input_value.strip().split()
                hour_minute = time_parts[0].split(":")
                hour = hour_minute[0]
                minute = hour_minute[1]
                
                # Check if AM/PM is specified
                period = None
                if len(time_parts) > 1:
                    period = time_parts[1].upper()
                
                success = self.pick_time(hour, minute, period)
                
                if success:
                    if auto_confirm:
                        confirm_success = self.confirm_selection()
                        return {
                            "success": confirm_success,
                            "message": f"Selected time: {hour}:{minute} {period or ''}",
                            "type": "time"
                        }
                    else:
                        return {
                            "success": True,
                            "message": f"Selected time: {hour}:{minute} {period or ''} (waiting for confirmation)",
                            "type": "time"
                        }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to select time: {hour}:{minute} {period or ''}",
                        "type": "time"
                    }
            
            else:
                self._log_activity(f"Could not determine picker type from input: {input_value}")
                return {
                    "success": False,
                    "message": f"Could not parse input value: {input_value}",
                    "type": "unknown"
                }
                
        except Exception as e:
            self._log_activity(f"Error handling scroll picker: {e}")
            return {
                "success": False,
                "message": f"Error handling scroll picker: {str(e)}",
                "type": "error"
            }
    
    def confirm_picker(self):
        """Confirm the current picker value."""
        return self.confirm_selection()
    
    def cancel_picker(self):
        """Cancel the current picker operation."""
        return self.cancel_selection()
