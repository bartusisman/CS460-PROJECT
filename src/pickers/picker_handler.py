from appium.webdriver.common.touch_action import TouchAction
import time
import re
from datetime import datetime
import calendar


class PickerHandler:
    """Handles interactions with iOS date and time pickers using hop-to-edge strategy."""
    
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
    
    def _get_visible_values(self, wheel_element):
        """
        Get the visible values in a picker wheel.
        
        Args:
            wheel_element: The picker wheel WebElement
            
        Returns:
            list: List of visible text values
        """
        try:
            # Do not use find_elements_by_xpath as it's deprecated
            # Use the page source to extract values instead
            page_source = self.driver.page_source
            
            # Try to get the direct value first
            try:
                current_value = wheel_element.get_attribute("value")
                if current_value:
                    return [current_value]
            except:
                pass
                
            # Get values based on the wheel type
            if "XCUIElementTypePickerWheel" in page_source:
                # Extract numbers for day and year
                day_matches = re.findall(r'(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})', page_source)
                if day_matches:
                    return [m for group in day_matches for m in group]
                
                # Look for month names
                month_names = [m for m in calendar.month_name if m]
                found_months = [m for m in month_names if m in page_source]
                if found_months:
                    return found_months
                
                # Look for years
                year_matches = re.findall(r'(20\d{2})', page_source)
                if year_matches:
                    return year_matches
            
            # If nothing found, return an empty list
            return []
        except Exception as e:
            self._log_activity(f"Error getting visible values: {e}")
            return []
    
    def _find_picker_wheels(self):
        """Find all picker wheel elements."""
        try:
            picker_wheels = self.driver.find_elements("class name", "XCUIElementTypePickerWheel")
            self._log_activity(f"Found {len(picker_wheels)} picker wheels")
            return picker_wheels
        except Exception as e:
            self._log_activity(f"Error finding picker wheels: {e}")
            return []
    
    def _click_element_position(self, wheel, x_offset=0, y_offset=0):
        """
        Click a specific position relative to an element's center.
        Uses WebDriver's native click methods instead of TouchAction.
        
        Args:
            wheel: The wheel element to click
            x_offset: Horizontal offset from center (positive = right)
            y_offset: Vertical offset from center (positive = down)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get element position and size
            size = wheel.size
            location = wheel.location
            
            # Calculate center
            center_x = location['x'] + size['width'] // 2
            center_y = location['y'] + size['height'] // 2
            
            # Calculate target position with offset
            target_x = center_x + x_offset
            target_y = center_y + y_offset
            
            # Use direct element click instead of TouchAction
            # For iOS, we can click the wheel element directly
            if abs(y_offset) < 10:  # Small offset - click center
                wheel.click()
            else:
                # For larger offsets, we need to calculate a new element to click
                # or use alternative method like swipe
                
                # Use a smaller swipe for more precise movement
                start_x = center_x
                start_y = center_y
                end_x = start_x
                end_y = target_y
                
                # Use swipe as an alternative to tap
                self.driver.swipe(start_x, start_y, end_x, end_y, 100)
            
            time.sleep(0.5)  # Wait for UI to update
            return True
            
        except Exception as e:
            self._log_activity(f"Error clicking element position: {e}")
            return False
    
    def _scroll_wheel(self, wheel, direction, distance_factor=1.0):
        """
        Scroll a picker wheel up or down using Appium's native scroll or swipe method.
        
        Args:
            wheel: The picker wheel element
            direction: 'up' to decrease value, 'down' to increase value
            distance_factor: Factor to adjust scroll distance (0.05 = micro scroll, 2.0 = large scroll)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # CORRECTED: Down scrolls to higher values, Up scrolls to lower values
            
            # Get wheel dimensions
            size = wheel.size
            location = wheel.location
            
            # Calculate scroll coordinates
            center_x = location['x'] + size['width'] // 2
            center_y = location['y'] + size['height'] // 2
            
            # Adjust distance based on the provided factor
            # Base distance is 20% of wheel height
            base_distance = int(size['height'] * 0.2)
            adjusted_distance = int(base_distance * distance_factor)
            
            # Ensure distance is sufficient to move the picker (minimum 25 pixels)
            # For micro-adjustments, we need at least 25px to ensure movement
            # For normal scrolls, ensure we move at least 15% of wheel height
            min_distance = max(25, int(size['height'] * 0.15))
            adjusted_distance = max(min_distance, min(adjusted_distance, int(size['height'] * 0.8)))
            
            self._log_activity(f"Scrolling {direction} with distance factor {distance_factor:.2f} (actual: {adjusted_distance}px)")
            
            if direction == 'up':
                # Scroll up (to decrease values)
                start_y = center_y
                end_y = center_y - adjusted_distance  # Move finger up to scroll up
            else:  # direction == 'down'
                # Scroll down (to increase values)
                start_y = center_y
                end_y = center_y + adjusted_distance  # Move finger down to scroll down
            
            # Calculate swipe duration based on distance - slower for smaller movements
            # Range from 100ms (micro) to 300ms (large)
            if distance_factor < 0.1:  # Micro-adjustment
                duration = 100  # Quick swipe for micro-adjustments
            elif distance_factor < 0.3:  # Small adjustment
                duration = 150  # Quick swipe for small adjustments
            elif distance_factor < 0.7:  # Medium adjustment
                duration = 200  # Medium swipe for moderate adjustments
            else:  # Large adjustment
                duration = 300  # Slow swipe for large adjustments
            
            # The mobile:scroll command doesn't support distance adjustment, so use direct swipe instead
            # which gives us precise control over the distance
            self.driver.swipe(center_x, start_y, center_x, end_y, duration)
            self._log_activity(f"Used swipe {direction} with distance {adjusted_distance}px and duration {duration}ms")
            
            # Adjust wait time based on distance - longer waits for larger scrolls
            wait_time = max(0.2, min(0.7, 0.2 + (distance_factor * 0.2)))  # between 0.2s and 0.7s
            time.sleep(wait_time)  # Allow UI to update
            return True
            
        except Exception as e:
            self._log_activity(f"Error scrolling wheel: {e}")
            return False
    
    def select_value_fast(self, wheel, target_value, value_type=None):
        """
        Fast hop-to-edge picker wheel selection.
        Clicks toward edges to quickly reach the target.
        
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
                # First try to get value directly from the wheel
                try:
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
                        
                        # CORRECTED AGAIN: Determine direction - REVERSED LOGIC
                        # When target > current, we need to scroll UP
                        # When target < current, we need to scroll DOWN
                        if value_type == 'month':
                            # For months, determine direction based on month index
                            direction_up = target_key > current_key  # Scroll UP for higher values
                        else:
                            # For numeric values, simple comparison
                            direction_up = target_key > current_key  # Scroll UP for higher values
                            
                        # Calculate distance factor based on how far we are from target
                        distance = abs(target_key - current_key)
                        
                        # Check for oscillation (if we keep bouncing between the same values)
                        oscillation_detected = False
                        if len(previous_values) >= 4:
                            # If the last 4 values oscillate between just 2 values
                            if len(set(previous_values[-4:])) <= 2:
                                # We're stuck in oscillation
                                oscillation_detected = True
                                self._log_activity(f"Oscillation detected, using stronger scroll")
                                
                        # Enable micro-adjustments when very close to target
                        if value_type == 'year' and distance <= 1:
                            using_micro_adjustment = True
                            
                        # Apply more effective scrolling strategy when very close to target
                        if using_micro_adjustment:
                            micro_adjustment_count += 1
                            
                            # Use stronger scroll when we're just 1 value away to ensure we can reach the target
                            if micro_adjustment_count <= 2:
                                distance_factor = 0.5  # Moderate scroll - enough to definitely move one value
                            elif micro_adjustment_count <= 4:
                                distance_factor = 0.35  # Medium-small scroll
                            else:
                                distance_factor = 0.25  # Small but still effective scroll
                                
                            # If we've been trying micro-adjustments but still not getting there
                            if micro_adjustment_count > 8:
                                # Try a full scroll to break out of potential stalemate
                                distance_factor = 0.8
                                micro_adjustment_count = 0
                                
                            self._log_activity(f"Using fine adjustment #{micro_adjustment_count} with factor {distance_factor}")
                            
                        # Use adaptive scaling based on value type and distance when not in micro-adjustment mode
                        elif oscillation_detected:
                            # Use stronger scroll for oscillation
                            distance_factor = 0.5
                        elif value_type == 'year':
                            if distance > 10:
                                distance_factor = 2.0  # Very far, use large swipes
                            elif distance > 5:
                                distance_factor = 1.5  # Far, use medium-large swipes
                            elif distance > 2:
                                distance_factor = 0.7  # Medium distance, use normal swipes
                            elif distance == 2:
                                distance_factor = 0.5  # Getting closer, use moderate swipes
                            else:  # distance == 1
                                distance_factor = 0.5  # Very close, use moderate swipes
                        elif value_type == 'month':
                            if distance > 6:
                                distance_factor = 2.0
                            elif distance > 3:
                                distance_factor = 1.5
                            elif distance > 1:
                                distance_factor = 0.7
                            else:
                                distance_factor = 0.5
                        elif value_type in ['day', 'hour']:
                            if distance > 15:
                                distance_factor = 2.0
                            elif distance > 8:
                                distance_factor = 1.5
                            elif distance > 4:
                                distance_factor = 0.7
                            elif distance > 1:
                                distance_factor = 0.5
                            else:
                                distance_factor = 0.5
                        elif value_type == 'minute':
                            if distance > 30:
                                distance_factor = 2.0
                            elif distance > 15:
                                distance_factor = 1.5
                            elif distance > 5:
                                distance_factor = 0.7
                            elif distance > 1:
                                distance_factor = 0.5
                            else:
                                distance_factor = 0.5
                        else:
                            # Default scaling
                            distance_factor = min(2.0, max(0.5, distance / 10.0))
                            
                        # Use the correct scroll direction with adaptive distance
                        self._log_activity(f"Scrolling {'up' if direction_up else 'down'} to reach {target_value} (distance: {distance})")
                        self._scroll_wheel(wheel, 'up' if direction_up else 'down', distance_factor)
                        
                        # Reduce wait time between attempts when making micro-adjustments
                        if using_micro_adjustment or oscillation_detected:
                            time.sleep(0.3)  # Shorter wait for micro-adjustments
                        else:
                            time.sleep(0.5)  # Normal wait for regular scrolls
                        
                    else:
                        # If we can't get the value, try using scroll as fallback
                        self._log_activity(f"Could not get current value, using fallback scroll")
                        # Use an educated guess for direction
                        if value_type == 'year':
                            # For years, if target is greater than 2020, likely need to scroll UP (to higher)
                            if target_key > 2020:
                                self._scroll_wheel(wheel, 'up', 1.0)
                            else:
                                self._scroll_wheel(wheel, 'down', 1.0)
                        else:
                            # For other types, just alternate
                            self._scroll_wheel(wheel, 'up' if attempts % 2 == 0 else 'down', 1.0)
                        
                except Exception as inner_e:
                    self._log_activity(f"Inner error: {inner_e}")
                    # If direct access fails, use a fallback scroll
                    self._scroll_wheel(wheel, 'up' if attempts % 2 == 0 else 'down', 1.0)
                
            except Exception as e:
                self._log_activity(f"Error in select_value_fast: {e}")
                # Try a simple scroll as last resort
                self._scroll_wheel(wheel, 'up' if attempts % 2 == 0 else 'down', 1.0)
                
            attempts += 1
            
        # After all attempts, try checking the value one more time
        try:
            current_value = wheel.get_attribute("value")
            if current_value and self._values_match(current_value, target_value, value_type):
                return True
        except:
            pass
            
        self._log_activity(f"Failed to set {value_type} wheel to {target_value} after {attempts} attempts")
        return False
    
    def _swipe_picker_wheel(self, wheel, direction, value_type=None):
        """
        DEPRECATED: Use _scroll_wheel instead.
        Fallback method to swipe a picker wheel up or down.
        
        Args:
            wheel: The picker wheel element
            direction: 'up' to decrease value, 'down' to increase value
            value_type: Type of wheel ('day', 'month', 'year', etc.)
        """
        # Redirect to the new function with the corrected direction logic
        return self._scroll_wheel(wheel, direction)
    
    def _values_match(self, current_value, target_value, value_type):
        """Check if current value matches the target value."""
        if value_type in ['day', 'year', 'hour', 'minute']:
            try:
                return int(current_value) == int(target_value)
            except (ValueError, TypeError):
                return False
        elif value_type == 'month':
            # Convert to lowercase and compare
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
        self._log_activity(f"Setting year to {target_year}")
        year_set = self.select_value_fast(year_wheel, target_year, 'year')
        if not year_set:
            # Try an alternative approach - this time with simple scrolls
            self._log_activity("Attempting fallback method for year")
            for _ in range(5):  # Try up to 5 scrolls
                current_year = year_wheel.get_attribute("value")
                try:
                    if int(current_year) == target_year:
                        year_set = True
                        break
                    elif int(current_year) < target_year:
                        # CORRECTED AGAIN: Scroll UP for higher values (REVERSED)
                        year_diff = target_year - int(current_year)
                        # Adaptive distance based on how far away we are
                        if year_diff > 10:
                            distance_factor = 2.0
                        elif year_diff > 5:
                            distance_factor = 1.5
                        elif year_diff > 2:
                            distance_factor = 1.0
                        elif year_diff == 2:
                            distance_factor = 0.5
                        else:  # year_diff == 1
                            distance_factor = 0.3
                            
                        self._scroll_wheel(year_wheel, 'up', distance_factor)
                    else:
                        # CORRECTED AGAIN: Scroll DOWN for lower values (REVERSED)
                        year_diff = int(current_year) - target_year
                        # Adaptive distance based on how far away we are
                        if year_diff > 10:
                            distance_factor = 2.0
                        elif year_diff > 5:
                            distance_factor = 1.5
                        elif year_diff > 2:
                            distance_factor = 1.0
                        elif year_diff == 2:
                            distance_factor = 0.5
                        else:  # year_diff == 1
                            distance_factor = 0.3
                            
                        self._scroll_wheel(year_wheel, 'down', distance_factor)
                except:
                    # If conversion fails, just try a scroll
                    self._scroll_wheel(year_wheel, 'up', 1.0)
                time.sleep(0.5)
        
        # Then set month
        self._log_activity(f"Setting month to {target_month}")
        month_set = self.select_value_fast(month_wheel, target_month, 'month')
        if not month_set:
            # Try an alternative approach - simplified scrolls for month
            self._log_activity("Attempting fallback method for month")
            # Try a series of scrolls to move through months
            current_month = None
            for _ in range(12):  # At most 12 scrolls for months
                try:
                    current_month = month_wheel.get_attribute("value")
                    if current_month and self._values_match(current_month, target_month, 'month'):
                        month_set = True
                        break
                        
                    # Determine direction based on month names
                    current_month_idx = self._to_key(current_month)
                    target_month_idx = self._to_key(target_month)
                    
                    # Calculate month difference for adaptive scrolling
                    month_diff = abs(target_month_idx - current_month_idx)
                    
                    # CORRECTED AGAIN: Scroll in the correct direction (REVERSED)
                    if current_month_idx < target_month_idx:
                        # Need to increase month, scroll UP
                        # Adaptive scroll based on how many months away
                        if month_diff > 6:
                            distance_factor = 2.0
                        elif month_diff > 3:
                            distance_factor = 1.5
                        elif month_diff > 1:
                            distance_factor = 1.0
                        else:
                            distance_factor = 0.5
                            
                        self._scroll_wheel(month_wheel, 'up', distance_factor)
                    else:
                        # Need to decrease month, scroll DOWN
                        # Adaptive scroll based on how many months away
                        if month_diff > 6:
                            distance_factor = 2.0
                        elif month_diff > 3:
                            distance_factor = 1.5
                        elif month_diff > 1:
                            distance_factor = 1.0
                        else:
                            distance_factor = 0.5
                            
                        self._scroll_wheel(month_wheel, 'down', distance_factor)
                except:
                    # If we can't determine direction, just try scrolling up
                    self._scroll_wheel(month_wheel, 'up', 1.0)
                
                time.sleep(0.5)
        
        # Finally set day
        self._log_activity(f"Setting day to {target_day}")
        day_set = self.select_value_fast(day_wheel, target_day, 'day')
        if not day_set:
            # Try an alternative approach - series of scrolls
            self._log_activity("Attempting fallback method for day")
            for _ in range(15):  # Most months have at most 31 days, but we'll limit scrolls
                current_day = day_wheel.get_attribute("value")
                try:
                    if int(current_day) == target_day:
                        day_set = True
                        break
                    elif int(current_day) < target_day:
                        # CORRECTED AGAIN: Scroll UP for higher values (REVERSED)
                        day_diff = target_day - int(current_day)
                        # Adaptive distance based on how far away we are
                        if day_diff > 15:
                            distance_factor = 2.0
                        elif day_diff > 8:
                            distance_factor = 1.5
                        elif day_diff > 3:
                            distance_factor = 1.0
                        elif day_diff > 1:
                            distance_factor = 0.5
                        else:
                            distance_factor = 0.3
                            
                        self._scroll_wheel(day_wheel, 'up', distance_factor)
                    else:
                        # CORRECTED AGAIN: Scroll DOWN for lower values (REVERSED)
                        day_diff = int(current_day) - target_day
                        # Adaptive distance based on how far away we are
                        if day_diff > 15:
                            distance_factor = 2.0
                        elif day_diff > 8:
                            distance_factor = 1.5
                        elif day_diff > 3:
                            distance_factor = 1.0
                        elif day_diff > 1:
                            distance_factor = 0.5
                        else:
                            distance_factor = 0.3
                            
                        self._scroll_wheel(day_wheel, 'down', distance_factor)
                except:
                    # If conversion fails, just try a scroll
                    self._scroll_wheel(day_wheel, 'up', 1.0)
                time.sleep(0.5)
        
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
        if not hour_set:
            # Fallback to simple scrolls approach for hour
            for _ in range(12):  # Try at most 12 scrolls (max hours)
                current_hour = picker_wheels[0].get_attribute("value")
                try:
                    if int(current_hour) == target_hour:
                        hour_set = True
                        break
                    elif int(current_hour) < target_hour:
                        # CORRECTED AGAIN: Scroll UP for higher values (REVERSED)
                        hour_diff = target_hour - int(current_hour)
                        # Adaptive distance based on how far away we are
                        if hour_diff > 6:
                            distance_factor = 2.0
                        elif hour_diff > 3:
                            distance_factor = 1.5
                        elif hour_diff > 1:
                            distance_factor = 1.0
                        else:
                            distance_factor = 0.5
                            
                        self._scroll_wheel(picker_wheels[0], 'up', distance_factor)
                    else:
                        # CORRECTED AGAIN: Scroll DOWN for lower values (REVERSED)
                        hour_diff = int(current_hour) - target_hour
                        # Adaptive distance based on how far away we are
                        if hour_diff > 6:
                            distance_factor = 2.0
                        elif hour_diff > 3:
                            distance_factor = 1.5
                        elif hour_diff > 1:
                            distance_factor = 1.0
                        else:
                            distance_factor = 0.5
                            
                        self._scroll_wheel(picker_wheels[0], 'down', distance_factor)
                except:
                    self._scroll_wheel(picker_wheels[0], 'up', 1.0)
                time.sleep(0.5)
        
        # Set minute
        minute_set = self.select_value_fast(picker_wheels[1], target_minute, 'minute')
        if not minute_set:
            # Fallback for minutes - simplified scrolls
            for _ in range(30):  # Limit scrolls to 30 (half of 60 minutes)
                current_minute = picker_wheels[1].get_attribute("value")
                try:
                    if int(current_minute) == target_minute:
                        minute_set = True
                        break
                    elif int(current_minute) < target_minute:
                        # CORRECTED AGAIN: Scroll UP for higher values (REVERSED)
                        minute_diff = target_minute - int(current_minute)
                        # Adaptive distance based on how far away we are in minutes
                        if minute_diff > 30:
                            distance_factor = 2.0
                        elif minute_diff > 15:
                            distance_factor = 1.5
                        elif minute_diff > 5:
                            distance_factor = 1.0
                        elif minute_diff > 1:
                            distance_factor = 0.5
                        else:
                            distance_factor = 0.15
                            
                        self._scroll_wheel(picker_wheels[1], 'up', distance_factor)
                    else:
                        # CORRECTED AGAIN: Scroll DOWN for lower values (REVERSED)
                        minute_diff = int(current_minute) - target_minute
                        # Adaptive distance based on how far away we are in minutes
                        if minute_diff > 30:
                            distance_factor = 2.0
                        elif minute_diff > 15:
                            distance_factor = 1.5
                        elif minute_diff > 5:
                            distance_factor = 1.0
                        elif minute_diff > 1:
                            distance_factor = 0.5
                        else:
                            distance_factor = 0.15
                            
                        self._scroll_wheel(picker_wheels[1], 'down', distance_factor)
                except:
                    self._scroll_wheel(picker_wheels[1], 'up', 1.0)
                time.sleep(0.5)
        
        # Set AM/PM if needed
        period_set = True  # Default to true if not using
        if using_period and len(picker_wheels) >= 3:
            period_set = self.select_value_fast(picker_wheels[2], target_period, 'period')
            if not period_set:
                # Simple toggle for period
                current_period = picker_wheels[2].get_attribute("value")
                if current_period and current_period.upper() != target_period.upper():
                    # Just toggle once for AM/PM - use small scroll for precision
                    self._scroll_wheel(picker_wheels[2], 'up', 0.5)
                    time.sleep(0.5)
                    # Check if it worked
                    current_period = picker_wheels[2].get_attribute("value")
                    period_set = (current_period and current_period.upper() == target_period.upper())
        
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
            
            try:
                confirm_button = self.driver.find_element("xpath", "//XCUIElementTypeButton[@name='Confirm' or @label='Confirm']")
                confirm_button.click()
                self._log_activity("Selection confirmed using XPath")
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
            
            try:
                cancel_button = self.driver.find_element("xpath", "//XCUIElementTypeButton[@name='Cancel' or @label='Cancel']")
                cancel_button.click()
                self._log_activity("Selection cancelled using XPath")
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
                
                self._log_activity(f"Attempting to pick date: {day} {month} {year}")
                success = self.pick_date(day, month, year)
                
                if success:
                    self._log_activity("Date selection successful")
                    if auto_confirm:
                        self._log_activity("Auto-confirming selection")
                        confirm_success = self.confirm_selection()
                        return {
                            "success": confirm_success,
                            "message": f"Selected date: {day} {month} {year}",
                            "type": "date"
                        }
                    else:
                        print("\n=== PICKER IS WAITING FOR CONFIRMATION ===")
                        print("Picker value set. The picker remains open.")
                        print("Use 'confirm picker' to accept or 'cancel picker' to cancel.")
                        print("=============================================\n")
                        
                        return {
                            "success": True,
                            "message": f"Selected date: {day} {month} {year} (waiting for confirmation)",
                            "type": "date"
                        }
                else:
                    self._log_activity("Date selection failed")
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
                
                self._log_activity(f"Attempting to pick time: {hour}:{minute} {period or ''}")
                success = self.pick_time(hour, minute, period)
                
                if success:
                    self._log_activity("Time selection successful")
                    if auto_confirm:
                        self._log_activity("Auto-confirming selection")
                        confirm_success = self.confirm_selection()
                        return {
                            "success": confirm_success,
                            "message": f"Selected time: {hour}:{minute} {period or ''}",
                            "type": "time"
                        }
                    else:
                        print("\n=== PICKER IS WAITING FOR CONFIRMATION ===")
                        print("Picker value set. The picker remains open.")
                        print("Use 'confirm picker' to accept or 'cancel picker' to cancel.")
                        print("=============================================\n")
                        
                        return {
                            "success": True,
                            "message": f"Selected time: {hour}:{minute} {period or ''} (waiting for confirmation)",
                            "type": "time"
                        }
                else:
                    self._log_activity("Time selection failed")
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
        self._log_activity("Confirming picker selection")
        return self.confirm_selection()
    
    def cancel_picker(self):
        """Cancel the current picker operation."""
        self._log_activity("Canceling picker selection")
        return self.cancel_selection()
