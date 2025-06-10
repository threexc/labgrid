# labgrid/planner.py
"""Interactive environment configuration generator for labgrid with curses TUI"""

import argparse
import sys
import curses
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

try:
    import yaml
except ImportError:
    print("PyYAML is required for the planner command. Install with: pip install PyYAML")
    sys.exit(1)

# Labgrid resource definitions based on actual labgrid resources
LABGRID_RESOURCES = {
    # GPIO Resources
    "SysfsGPIO": {
        "description": "GPIO pin accessed through sysfs",
        "category": "GPIO",
        "properties": {
            "index": {"type": "int", "description": "GPIO pin number", "required": True}
        }
    },
    "MatchedSysfsGPIO": {
        "description": "GPIO pin with device matching",
        "category": "GPIO", 
        "properties": {
            "match": {"type": "dict", "description": "Device matching criteria", "required": True},
            "index": {"type": "int", "description": "GPIO pin number", "required": True}
        }
    },
    
    # Serial Resources  
    "SerialPort": {
        "description": "Generic serial port device",
        "category": "Serial",
        "properties": {
            "port": {"type": "str", "description": "Serial port path (e.g., /dev/ttyUSB0)", "required": True},
            "speed": {"type": "int", "description": "Baud rate (default: 115200)", "required": False}
        }
    },
    "USBSerialPort": {
        "description": "USB serial port with matching",
        "category": "Serial",
        "properties": {
            "match": {"type": "dict", "description": "Device matching criteria", "required": True},
            "speed": {"type": "int", "description": "Baud rate (default: 115200)", "required": False}
        }
    },
    "RawSerialPort": {
        "description": "Raw serial port without protocols",
        "category": "Serial",
        "properties": {
            "port": {"type": "str", "description": "Serial port path", "required": True},
            "speed": {"type": "int", "description": "Baud rate", "required": False}
        }
    },
    
    # Network Resources
    "NetworkInterface": {
        "description": "Network interface for testing",
        "category": "Network",
        "properties": {
            "ifname": {"type": "str", "description": "Network interface name (e.g., eth0)", "required": True},
            "address": {"type": "str", "description": "IP address or hostname", "required": False}
        }
    },
    "USBEthernetPort": {
        "description": "USB Ethernet adapter",
        "category": "Network",
        "properties": {
            "match": {"type": "dict", "description": "Device matching criteria", "required": True}
        }
    },
    
    # Power Resources
    "ManualPowerPort": {
        "description": "Manually controlled power",
        "category": "Power",
        "properties": {}
    },
    "ExternalPowerPort": {
        "description": "External power via commands",
        "category": "Power",
        "properties": {
            "cmd_on": {"type": "str", "description": "Command to turn power on", "required": True},
            "cmd_off": {"type": "str", "description": "Command to turn power off", "required": True},
            "cmd_cycle": {"type": "str", "description": "Command to cycle power", "required": False}
        }
    },
    "NetworkPowerPort": {
        "description": "Network-controlled power",
        "category": "Power",
        "properties": {
            "host": {"type": "str", "description": "Hostname or IP address", "required": True},
            "index": {"type": "int", "description": "Port index", "required": True}
        }
    },
    "USBPowerPort": {
        "description": "USB power control port",
        "category": "Power",
        "properties": {
            "match": {"type": "dict", "description": "Device matching criteria", "required": True},
            "index": {"type": "int", "description": "Port index", "required": True}
        }
    },
    "HttpDigitalOutput": {
        "description": "HTTP-controlled digital output",
        "category": "Power",
        "properties": {
            "url": {"type": "str", "description": "Base URL for HTTP requests", "required": True},
            "index": {"type": "int", "description": "Output index/channel", "required": True}
        }
    },
    
    # Storage Resources
    "USBMassStorage": {
        "description": "USB mass storage device",
        "category": "Storage",
        "properties": {
            "match": {"type": "dict", "description": "Device matching criteria", "required": True}
        }
    },
    "NetworkMassStorage": {
        "description": "Network-attached storage",
        "category": "Storage",
        "properties": {
            "host": {"type": "str", "description": "Hostname or IP address", "required": True},
            "rootpath": {"type": "str", "description": "Root path on the storage", "required": False}
        }
    },
    
    # Android/Mobile Resources
    "AndroidFastboot": {
        "description": "Android fastboot interface",
        "category": "Mobile",
        "properties": {
            "match": {"type": "dict", "description": "Device matching criteria", "required": True}
        }
    },
    "USBADBDevice": {
        "description": "Android ADB device",
        "category": "Mobile",
        "properties": {
            "match": {"type": "dict", "description": "Device matching criteria", "required": True}
        }
    },
    "AndroidUSBFastboot": {
        "description": "Android USB fastboot",
        "category": "Mobile",
        "properties": {
            "match": {"type": "dict", "description": "Device matching criteria", "required": True}
        }
    },
    
    # Remote Resources
    "RemotePlace": {
        "description": "Remote place for distributed testing",
        "category": "Remote",
        "properties": {
            "name": {"type": "str", "description": "Remote place name", "required": True}
        }
    },
    "NetworkService": {
        "description": "Network service endpoint",
        "category": "Remote",
        "properties": {
            "address": {"type": "str", "description": "Service address", "required": True},
            "username": {"type": "str", "description": "Username for authentication", "required": False}
        }
    },
    
    # Video/Display Resources
    "USBVideo": {
        "description": "USB video capture device",
        "category": "Video",
        "properties": {
            "match": {"type": "dict", "description": "Device matching criteria", "required": True}
        }
    },
    
    # Test Equipment Resources
    "NetworkSigrokDevice": {
        "description": "Network Sigrok device",
        "category": "TestEquipment",
        "properties": {
            "host": {"type": "str", "description": "Hostname or IP address", "required": True},
            "device": {"type": "str", "description": "Device identifier", "required": True}
        }
    },
    "USBSigrokDevice": {
        "description": "USB Sigrok device",
        "category": "TestEquipment",
        "properties": {
            "match": {"type": "dict", "description": "Device matching criteria", "required": True},
            "driver": {"type": "str", "description": "Sigrok driver name", "required": True}
        }
    }
}

# Labgrid driver definitions
LABGRID_DRIVERS = {
    # Serial Drivers
    "SerialDriver": {
        "description": "Generic serial communication driver",
        "category": "Serial",
        "properties": {}
    },
    
    # GPIO Drivers  
    "GpioDigitalOutputDriver": {
        "description": "GPIO digital output control driver",
        "category": "GPIO",
        "properties": {}
    },
    
    # Power Drivers
    "PowerResetDriver": {
        "description": "Power reset control driver", 
        "category": "Power",
        "properties": {
            "delay": {"type": "float", "description": "Reset delay in seconds", "required": False}
        }
    },
    "DigitalOutputPowerDriver": {
        "description": "Digital output power control driver",
        "category": "Power", 
        "properties": {}
    },
    "ExternalPowerDriver": {
        "description": "External command power driver",
        "category": "Power",
        "properties": {}
    },
    "NetworkPowerDriver": {
        "description": "Network power control driver",
        "category": "Power",
        "properties": {}
    },
    
    # Shell/Console Drivers
    "ShellDriver": {
        "description": "Interactive shell driver",
        "category": "Shell",
        "properties": {
            "prompt": {"type": "str", "description": "Shell prompt pattern", "required": False},
            "login_prompt": {"type": "str", "description": "Login prompt pattern", "required": False},
            "username": {"type": "str", "description": "Username for login", "required": False},
            "password": {"type": "str", "description": "Password for login", "required": False}
        }
    },
    "SSHDriver": {
        "description": "SSH connection driver",
        "category": "Shell",
        "properties": {
            "keyfile": {"type": "str", "description": "SSH private key file path", "required": False}
        }
    },
    
    # Bootloader Drivers
    "UBootDriver": {
        "description": "U-Boot bootloader driver",
        "category": "Bootloader",
        "properties": {
            "prompt": {"type": "str", "description": "U-Boot prompt pattern", "required": False},
            "autoboot": {"type": "str", "description": "Autoboot interrupt sequence", "required": False},
            "interrupt": {"type": "str", "description": "Interrupt character", "required": False}
        }
    },
    "BareboxDriver": {
        "description": "Barebox bootloader driver",
        "category": "Bootloader",
        "properties": {
            "prompt": {"type": "str", "description": "Barebox prompt pattern", "required": False}
        }
    },
    
    # Android/Mobile Drivers
    "ADBDriver": {
        "description": "Android ADB driver",
        "category": "Mobile",
        "properties": {}
    },
    "FastbootDriver": {
        "description": "Android Fastboot driver", 
        "category": "Mobile",
        "properties": {}
    },
    
    # File Transfer Drivers
    "FileTransferDriver": {
        "description": "File transfer driver",
        "category": "FileTransfer",
        "properties": {}
    },
    
    # Test Equipment Drivers
    "SigrokDriver": {
        "description": "Sigrok measurement driver",
        "category": "TestEquipment",
        "properties": {
            "capture_file": {"type": "str", "description": "Capture output file", "required": False}
        }
    },
    
    # Video Drivers
    "USBVideoDriver": {
        "description": "USB video capture driver",
        "category": "Video",
        "properties": {}
    },
    
    # Strategy Drivers
    "DockerStrategy": {
        "description": "Docker container strategy",
        "category": "Strategy",
        "properties": {
            "image_uri": {"type": "str", "description": "Docker image URI", "required": True},
            "command": {"type": "str", "description": "Command to run in container", "required": False},
            "host_config": {"type": "dict", "description": "Docker host configuration", "required": False}
        }
    },
    "ShellStrategy": {
        "description": "Shell command execution strategy",
        "category": "Strategy", 
        "properties": {}
    }
}

@dataclass
class ResourceItem:
    name: str
    description: str
    category: str
    selected: bool = False

@dataclass
class Column:
    category: str
    resources: List[ResourceItem]
    x: int
    width: int

class ResourceSelector:
    def __init__(self, stdscr, item_type="resources"):
        self.stdscr = stdscr
        self.item_type = item_type  # "resources" or "drivers"
        self.selected_items = set()
        self.current_col = 0
        self.current_row = 0
        self.columns = []
        self.setup_columns()
        
        # Initialize curses colors
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)    # Header
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)    # Current selection (dark on cyan)
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Selected item
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Unused
        curses.init_pair(5, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Instructions/descriptions
    
    def get_items_dict(self):
        """Get the appropriate items dictionary based on type"""
        return LABGRID_DRIVERS if self.item_type == "drivers" else LABGRID_RESOURCES
        
    def setup_columns(self):
        """Organize items into columns by category"""
        categories = {}
        items_dict = self.get_items_dict()
        
        # Group items by category
        for name, info in items_dict.items():
            category = info.get("category", "Other")
            if category not in categories:
                categories[category] = []
            categories[category].append(ResourceItem(
                name=name,
                description=info.get("description", ""),
                category=category
            ))
        
        # Define column mapping based on item type
        if self.item_type == "drivers":
            column_mapping = {
                0: ["Serial", "GPIO"],           # Column 1: Serial + GPIO drivers
                1: ["Power", "Shell"],           # Column 2: Power + Shell drivers  
                2: ["Bootloader", "Mobile"],     # Column 3: Bootloader + Mobile drivers
                3: ["FileTransfer", "Video"],    # Column 4: FileTransfer + Video drivers
                4: ["TestEquipment", "Strategy", "Other"]  # Column 5: TestEquipment + Strategy + Other
            }
        else:
            # Original resource mapping
            column_mapping = {
                0: ["GPIO", "Serial"],      # Column 1: GPIO + Serial
                1: ["Mobile", "Storage"],   # Column 2: Mobile + Storage  
                2: ["Network", "TestEquipment"],  # Column 3: Network + TestEquipment
                3: ["Power"],               # Column 4: Power only
                4: ["Remote", "Video", "Other"]  # Column 5: Remote + Video + Other
            }
        
        # Create columns
        height, width = self.stdscr.getmaxyx()
        num_cols = 5
        col_width = max(20, (width - 6) // num_cols)  # Leave space between columns
        
        self.columns = []
        x_pos = 1
        
        for col_idx in range(num_cols):
            column_categories = column_mapping.get(col_idx, [])
            column_resources = []
            
            for category in column_categories:
                if category in categories:
                    column_resources.extend(categories[category])
            
            if column_resources:  # Only create column if it has resources
                self.columns.append(Column(
                    category=" / ".join(column_categories),  # Show combined category names
                    resources=column_resources,
                    x=x_pos,
                    width=col_width
                ))
                x_pos += col_width + 1
    
    def draw_header(self):
        """Draw the header with title and instructions"""
        height, width = self.stdscr.getmaxyx()
        
        # Title
        item_type_title = "Driver" if self.item_type == "drivers" else "Resource"
        title = f"Labgrid Environment Planner - {item_type_title} Selection"
        self.stdscr.addstr(0, (width - len(title)) // 2, title, curses.color_pair(1) | curses.A_BOLD)
        
        # Instructions
        instructions = [
            "Arrow Keys: Navigate  |  Space: Toggle Selection  |  Enter: Continue  |  Q: Quit"
        ]
        for i, instruction in enumerate(instructions):
            self.stdscr.addstr(height - 2 + i, (width - len(instruction)) // 2, 
                             instruction, curses.color_pair(5))
    
    def draw_columns(self):
        """Draw all resource columns"""
        height, _ = self.stdscr.getmaxyx()
        
        current_resource_description = None
        
        for col_idx, column in enumerate(self.columns):
            # Draw column header - no special highlighting
            header = f"═══ {column.category} ═══"
            header_y = 2
            
            # Always use the same color for column headers (no highlighting based on current column)
            self.stdscr.addstr(header_y, column.x, header[:column.width], 
                             curses.color_pair(1))
            
            # Group resources by their original category for display
            current_category = None
            category_offset = 0
            display_row = 0  # Track display row separately from resource index
            
            for resource_idx, resource in enumerate(column.resources):
                # Add category separator when category changes
                if resource.category != current_category:
                    if current_category is not None:
                        category_offset += 1  # Add space between categories
                        display_row += 1
                    current_category = resource.category
                    
                    # Draw category subheader
                    y_pos = header_y + 2 + display_row
                    if y_pos < height - 6:  # Leave more space for description and status
                        category_header = f"-- {current_category} --"
                        try:
                            self.stdscr.addstr(y_pos, column.x, category_header[:column.width], 
                                             curses.color_pair(5) | curses.A_DIM)
                        except curses.error:
                            pass
                    display_row += 1
                
                y_pos = header_y + 2 + display_row
                if y_pos >= height - 6:  # Leave space for description and status
                    break
                    
                # Format resource display
                checkbox = "[×]" if resource.selected else "[ ]"
                resource_text = f"{checkbox} {resource.name}"
                
                # Truncate if too long
                display_text = resource_text[:column.width - 1]
                
                # Determine color/style - check if this is the currently selected item
                attrs = curses.A_NORMAL
                color_pair = 0
                
                # Check if this is the currently highlighted item FIRST (highest priority)
                if col_idx == self.current_col and resource_idx == self.current_row:
                    color_pair = 2  # White on blue for current selection
                    attrs = curses.A_REVERSE | curses.A_BOLD
                    # Store description for current resource
                    current_resource_description = f"{resource.name}: {resource.description}"
                elif resource.selected:
                    color_pair = 3  # Green for selected items
                    attrs = curses.A_BOLD
                
                try:
                    self.stdscr.addstr(y_pos, column.x, display_text, 
                                     curses.color_pair(color_pair) | attrs)
                except curses.error:
                    pass  # Ignore if we can't write at this position
                
                display_row += 1
        
        # Draw description above the selection summary
        if current_resource_description:
            self.draw_current_description(current_resource_description)
    
    def draw_current_description(self, description: str):
        """Draw the description of the currently selected resource"""
        height, width = self.stdscr.getmaxyx()
        
        # Truncate description to fit screen width
        max_desc_width = width - 4
        if len(description) > max_desc_width:
            description = description[:max_desc_width - 3] + "..."
        
        try:
            # Clear the description line first
            self.stdscr.addstr(height - 5, 2, " " * (width - 4), curses.A_NORMAL)
            # Draw description above the selection summary (height - 5)
            self.stdscr.addstr(height - 5, 2, description, curses.color_pair(5))
        except curses.error:
            pass
    
    def draw_selection_summary(self):
        """Draw summary of selected items"""
        height, width = self.stdscr.getmaxyx()
        
        selected_count = sum(1 for col in self.columns for res in col.resources if res.selected)
        item_type_name = "drivers" if self.item_type == "drivers" else "resources"
        summary = f"Selected: {selected_count} {item_type_name}"
        
        try:
            self.stdscr.addstr(height - 4, 1, summary, curses.color_pair(3) | curses.A_BOLD)
        except curses.error:
            pass
    
    def handle_input(self, key):
        """Handle keyboard input"""
        if not self.columns:
            return True
            
        current_column = self.columns[self.current_col]
        
        if key == ord('q') or key == ord('Q'):
            return False
        elif key == ord('\n') or key == ord('\r'):  # Enter
            return False
        elif key == ord(' '):  # Space - toggle selection
            if self.current_row < len(current_column.resources):
                resource = current_column.resources[self.current_row]
                resource.selected = not resource.selected
        elif key == curses.KEY_LEFT:
            if self.current_col > 0:
                self.current_col -= 1
                self.current_row = min(self.current_row, len(self.columns[self.current_col].resources) - 1)
        elif key == curses.KEY_RIGHT:
            if self.current_col < len(self.columns) - 1:
                self.current_col += 1
                self.current_row = min(self.current_row, len(self.columns[self.current_col].resources) - 1)
        elif key == curses.KEY_UP:
            if self.current_row > 0:
                self.current_row -= 1
        elif key == curses.KEY_DOWN:
            if self.current_row < len(current_column.resources) - 1:
                self.current_row += 1
        
        return True
    
    def run(self):
        """Main TUI loop"""
        curses.curs_set(0)  # Hide cursor
        
        while True:
            self.stdscr.clear()
            self.draw_header()
            self.draw_columns()
            self.draw_selection_summary()
            self.stdscr.refresh()
            
            key = self.stdscr.getch()
            if not self.handle_input(key):
                break
        
        # Return selected items
        selected = []
        for column in self.columns:
            for resource in column.resources:
                if resource.selected:
                    selected.append(resource.name)
        
        return selected

def get_resource_properties(resource_class: str) -> Dict[str, Any]:
    """Get properties for a specific resource class"""
    return LABGRID_RESOURCES.get(resource_class, {}).get("properties", {})

def get_driver_properties(driver_class: str) -> Dict[str, Any]:
    """Get properties for a specific driver class"""
    return LABGRID_DRIVERS.get(driver_class, {}).get("properties", {})

def load_existing_config(filepath: str) -> Dict[str, Any]:
    """Load existing YAML configuration file"""
    try:
        with open(filepath, 'r') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        return {}

def save_config(config: Dict[str, Any], filepath: str) -> None:
    """Save configuration to YAML file"""
    try:
        with open(filepath, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        print(f"Configuration saved to {filepath}")
    except Exception as e:
        print(f"Error saving configuration: {e}")

def prompt_for_match_criteria() -> Dict[str, str]:
    """Prompt user for device matching criteria"""
    match_dict = {}
    print("\nDevice matching criteria:")
    
    common_keys = [
        "@SUBSYSTEM", "@ID_SERIAL_SHORT", "@ID_VENDOR_ID", "@ID_MODEL_ID", 
        "@DEVNAME", "@ID_PATH", "@ID_USB_INTERFACE_NUM", "@DEVPATH"
    ]
    
    print("Common matching keys:", ", ".join(common_keys))
    print("Example: @SUBSYSTEM=usb, @ID_SERIAL_SHORT=ABC123")
    print("Press Enter with empty key to finish")
    
    while True:
        key = input("Match key (e.g., @SUBSYSTEM): ").strip()
        if not key:
            break
            
        value = input(f"Value for {key}: ").strip()
        if value:
            match_dict[key] = value
        
        # Ask if they want to add another match criterion
        another = input("Add another match criterion? [y/N]: ").strip().lower()
        if another not in ['y', 'yes']:
            break
    
    return match_dict

def prompt_for_property_value(prop_name: str, prop_info: Dict[str, Any]) -> Any:
    """Prompt user for a property value based on its type"""
    prop_type = prop_info.get("type", "str")
    description = prop_info.get("description", "")
    
    prompt_text = f"{prop_name}"
    if description:
        prompt_text += f" ({description})"
    prompt_text += ": "
    
    if prop_type == "dict" and prop_name == "match":
        return prompt_for_match_criteria()
    elif prop_type == "int":
        while True:
            try:
                value = input(prompt_text).strip()
                return int(value) if value else None
            except ValueError:
                print("Please enter a valid integer")
    else:
        return input(prompt_text).strip() or None

def create_resource_skeleton(resource_class: str, instance_num: int) -> Tuple[str, Dict[str, Any]]:
    """Create a resource skeleton with all properties as placeholders"""
    properties = get_resource_properties(resource_class)
    resource_config = {"cls": resource_class}
    
    # Generate a default label
    base_name = resource_class.lower().replace('matched', '').replace('usb', '').replace('sysfs', '')
    if instance_num > 1:
        label = f"{base_name}-{instance_num}"
    else:
        label = base_name
    
    # Add all properties with appropriate placeholder values
    for prop_name, prop_info in properties.items():
        prop_type = prop_info.get("type", "str")
        
        # Replace "index" with "pin" for GPIO resources
        if prop_name == "index" and "GPIO" in resource_class:
            prop_name = "pin"
        
        if prop_type == "dict" and prop_name == "match":
            resource_config[prop_name] = {
                "@SUBSYSTEM": "usb",
                "@ID_SERIAL_SHORT": "CHANGEME"
            }
        elif prop_type == "int":
            if "port" in prop_name.lower() or "index" in prop_name.lower() or "pin" in prop_name.lower():
                resource_config[prop_name] = 0
            elif "speed" in prop_name.lower() or "baud" in prop_name.lower():
                resource_config[prop_name] = 115200
            else:
                resource_config[prop_name] = 0
        elif prop_type == "str":
            if "port" in prop_name.lower():
                resource_config[prop_name] = "/dev/ttyUSB0"
            elif "host" in prop_name.lower() or "address" in prop_name.lower():
                resource_config[prop_name] = "192.168.1.100"
            elif "url" in prop_name.lower():
                resource_config[prop_name] = "http://192.168.1.100"
            elif "cmd" in prop_name.lower():
                resource_config[prop_name] = "echo 'command here'"
            elif "name" in prop_name.lower():
                resource_config[prop_name] = "remote-place-name"
            elif "ifname" in prop_name.lower():
                resource_config[prop_name] = "eth0"
            elif "path" in prop_name.lower():
                resource_config[prop_name] = "/path/to/storage"
            elif "device" in prop_name.lower():
                resource_config[prop_name] = "device-identifier"
            elif "driver" in prop_name.lower():
                resource_config[prop_name] = "driver-name"
            elif "prompt" in prop_name.lower():
                resource_config[prop_name] = "=> "
            elif "username" in prop_name.lower():
                resource_config[prop_name] = "user"
            else:
                resource_config[prop_name] = "CHANGEME"
    
    return label, resource_config

def create_driver_skeleton(driver_class: str, instance_num: int) -> Tuple[str, Dict[str, Any]]:
    """Create a driver skeleton with all properties as placeholders"""
    properties = get_driver_properties(driver_class)
    
    # Generate a default name
    base_name = driver_class.lower().replace('driver', '').replace('strategy', '')
    if instance_num > 1:
        name = f"{base_name}-{instance_num}"
    else:
        name = base_name
    
    # Driver structure with class name as key and properties including name and bindings
    driver_config = {
        "name": name,
        "bindings": {}
    }
    
    # Add bindings based on driver type
    if "Serial" in driver_class:
        driver_config["bindings"]["port"] = "CHANGEME-serial-port"
    elif "GPIO" in driver_class or "DigitalOutput" in driver_class:
        driver_config["bindings"]["gpio"] = "CHANGEME-gpio"
    elif "Power" in driver_class:
        if "DigitalOutput" in driver_class:
            driver_config["bindings"]["gpio"] = "CHANGEME-power-gpio"
        else:
            driver_config["bindings"]["port"] = "CHANGEME-power-port"
    elif "Shell" in driver_class or "SSH" in driver_class:
        driver_config["bindings"]["port"] = "CHANGEME-serial-port"
    elif "UBoot" in driver_class or "Barebox" in driver_class:
        driver_config["bindings"]["port"] = "CHANGEME-serial-port"
    elif "ADB" in driver_class:
        driver_config["bindings"]["adb"] = "CHANGEME-adb-device"
    elif "Fastboot" in driver_class:
        driver_config["bindings"]["fastboot"] = "CHANGEME-fastboot-device"
    elif "FileTransfer" in driver_class:
        driver_config["bindings"]["shell"] = "CHANGEME-shell-driver"
    elif "Video" in driver_class:
        driver_config["bindings"]["video"] = "CHANGEME-video-device"
    elif "Sigrok" in driver_class:
        driver_config["bindings"]["sigrok"] = "CHANGEME-sigrok-device"
    elif "Docker" in driver_class:
        driver_config["bindings"]["shell"] = "CHANGEME-shell-driver"
    else:
        driver_config["bindings"]["resource"] = "CHANGEME-resource"
    
    # Add driver-specific properties with appropriate placeholder values
    for prop_name, prop_info in properties.items():
        prop_type = prop_info.get("type", "str")
        
        if prop_type == "dict":
            if "host_config" in prop_name.lower():
                driver_config[prop_name] = {
                    "binds": ["/host/path:/container/path"],
                    "privileged": False
                }
            else:
                driver_config[prop_name] = {"key": "CHANGEME"}
        elif prop_type == "float":
            if "delay" in prop_name.lower():
                driver_config[prop_name] = 1.0
            else:
                driver_config[prop_name] = 0.0
        elif prop_type == "str":
            if "prompt" in prop_name.lower():
                driver_config[prop_name] = "$ "
            elif "login_prompt" in prop_name.lower():
                driver_config[prop_name] = "login: "
            elif "username" in prop_name.lower():
                driver_config[prop_name] = "root"
            elif "password" in prop_name.lower():
                driver_config[prop_name] = "password123"
            elif "keyfile" in prop_name.lower():
                driver_config[prop_name] = "~/.ssh/id_rsa"
            elif "autoboot" in prop_name.lower() or "interrupt" in prop_name.lower():
                driver_config[prop_name] = " "
            elif "image_uri" in prop_name.lower():
                driver_config[prop_name] = "docker://ubuntu:latest"
            elif "command" in prop_name.lower():
                driver_config[prop_name] = "/bin/bash"
            elif "capture_file" in prop_name.lower():
                driver_config[prop_name] = "/tmp/capture.sr"
            else:
                driver_config[prop_name] = "CHANGEME"
    
    return driver_class, driver_config

def remove_comments_from_yaml(yaml_content: str) -> str:
    """Remove all comments from YAML content"""
    lines = yaml_content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Find the position of '#' that's not inside quotes
        comment_pos = -1
        in_single_quote = False
        in_double_quote = False
        
        for i, char in enumerate(line):
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif char == '#' and not in_single_quote and not in_double_quote:
                comment_pos = i
                break
        
        if comment_pos >= 0:
            # Remove comment and trailing whitespace
            line = line[:comment_pos].rstrip()
        
        # Only add non-empty lines or lines that aren't just whitespace
        if line.strip() or (not line.strip() and cleaned_lines and cleaned_lines[-1].strip()):
            cleaned_lines.append(line)
    
    # Remove trailing empty lines
    while cleaned_lines and not cleaned_lines[-1].strip():
        cleaned_lines.pop()
    
    return '\n'.join(cleaned_lines)

def generate_yaml(target_name: str, location: str, selected_resources: List[str], selected_drivers: List[str] = None, is_driver_file: bool = False) -> str:
    """Generate YAML configuration"""
    
    if is_driver_file:
        # Driver file structure: targets -> target_name -> resources/drivers
        config = {}
        config["targets"] = {}
        config["targets"][target_name] = {}
        config["targets"][target_name]["resources"] = {}
        config["targets"][target_name]["drivers"] = []
        
        # Add drivers as a list under the drivers section
        if selected_drivers:
            driver_counts = {}
            
            for driver_class in selected_drivers:
                if driver_class not in driver_counts:
                    driver_counts[driver_class] = 0
                driver_counts[driver_class] += 1
                
                instance_num = driver_counts[driver_class]
                driver_class_name, driver_config = create_driver_skeleton(driver_class, instance_num)
                
                # Create driver entry as {DriverClass: config}
                driver_entry = {driver_class_name: driver_config}
                config["targets"][target_name]["drivers"].append(driver_entry)
    else:
        # Resource file structure: target_name -> location + resources
        config = {}
        config[target_name] = {}
        config[target_name]["location"] = location
        
        # Count instances of each resource type
        resource_counts = {}
        
        for resource_class in selected_resources:
            if resource_class not in resource_counts:
                resource_counts[resource_class] = 0
            resource_counts[resource_class] += 1
            
            instance_num = resource_counts[resource_class]
            label, resource_config = create_resource_skeleton(resource_class, instance_num)
            
            config[target_name][label] = resource_config
    
    # Convert to YAML string with no comments
    yaml_str = yaml.dump(config, default_flow_style=False, indent=2, sort_keys=False, 
                        allow_unicode=True, encoding=None)
    
    # Remove any comments that might have been added
    yaml_str = remove_comments_from_yaml(yaml_str)
    
    return yaml_str
    """Generate YAML configuration with comments for all properties"""
    
    if is_driver_file:
        # Driver file structure: targets -> target_name -> resources/drivers
        config = {}
        config["targets"] = {}
        config["targets"][target_name] = {}
        config["targets"][target_name]["resources"] = {}
        config["targets"][target_name]["drivers"] = []
        
        # Add drivers as a list under the drivers section
        if selected_drivers:
            driver_counts = {}
            
            for driver_class in selected_drivers:
                if driver_class not in driver_counts:
                    driver_counts[driver_class] = 0
                driver_counts[driver_class] += 1
                
                instance_num = driver_counts[driver_class]
                driver_class_name, driver_config = create_driver_skeleton(driver_class, instance_num)
                
                # Create driver entry as {DriverClass: config}
                driver_entry = {driver_class_name: driver_config}
                config["targets"][target_name]["drivers"].append(driver_entry)
    else:
        # Resource file structure: target_name -> location + resources
        config = {}
        config[target_name] = {}
        config[target_name]["location"] = location
        
        # Count instances of each resource type
        resource_counts = {}
        
        for resource_class in selected_resources:
            if resource_class not in resource_counts:
                resource_counts[resource_class] = 0
            resource_counts[resource_class] += 1
            
            instance_num = resource_counts[resource_class]
            label, resource_config = create_resource_skeleton(resource_class, instance_num)
            
            config[target_name][label] = resource_config
    
    # Convert to YAML string with consistent ordering
    yaml_str = yaml.dump(config, default_flow_style=False, indent=2, sort_keys=False)
    
    # Add helpful comments
    lines = yaml_str.split('\n')
    result_lines = []
    
    for line in lines:
        result_lines.append(line)
        
        # Add comments after certain fields
        if '"CHANGEME"' in line or "'CHANGEME'" in line:
            indent = len(line) - len(line.lstrip())
            result_lines.append(' ' * indent + '# TODO: Replace CHANGEME with actual value')
        elif '@ID_SERIAL_SHORT: CHANGEME' in line:
            indent = len(line) - len(line.lstrip())
            result_lines.append(' ' * indent + '# Find with: udevadm info --name=/dev/ttyUSB0 --attribute-walk')
        elif 'cls:' in line:
            # Add description comment for the resource/driver class
            for resource_class, info in LABGRID_RESOURCES.items():
                if resource_class in line:
                    indent = len(line) - len(line.lstrip())
                    result_lines.append(' ' * indent + f'# {info.get("description", "")}')
                    break
            else:
                for driver_class, info in LABGRID_DRIVERS.items():
                    if driver_class in line:
                        indent = len(line) - len(line.lstrip())
                        result_lines.append(' ' * indent + f'# {info.get("description", "")}')
                        break
    
    return '\n'.join(result_lines)

def ensure_yaml_extension(filename: str) -> str:
    """Ensure filename has .yaml extension"""
    path = Path(filename)
    if path.suffix.lower() not in ['.yaml', '.yml']:
        return str(path.with_suffix('.yaml'))
    return filename

def get_driver_filename(base_filename: str) -> str:
    """Generate driver filename by appending -drivers before the extension"""
    # First ensure the base filename has .yaml extension
    base_filename = ensure_yaml_extension(base_filename)
    path = Path(base_filename)
    stem = path.stem
    suffix = path.suffix
    
    return str(path.parent / f"{stem}-drivers{suffix}")

def configure_resource_instances(selected_resources: List[str]) -> Dict[str, Any]:
    """Generate skeleton configurations for selected resources"""
    target_config = {}
    
    print(f"\nGenerating configuration skeletons for {len(selected_resources)} resource types...")
    
    # Count instances of each resource type
    resource_counts = {}
    
    for resource_class in selected_resources:
        if resource_class not in resource_counts:
            resource_counts[resource_class] = 0
        resource_counts[resource_class] += 1
        
        instance_num = resource_counts[resource_class]
        label, resource_config = create_resource_skeleton(resource_class, instance_num)
        
        target_config[label] = resource_config
        print(f"  • Generated skeleton for '{label}' ({resource_class})")
    
    return target_config

def configure_driver_instances(selected_drivers: List[str]) -> List[Dict[str, Any]]:
    """Generate skeleton configurations for selected drivers"""
    driver_list = []
    
    print(f"\nGenerating configuration skeletons for {len(selected_drivers)} driver types...")
    
    # Count instances of each driver type
    driver_counts = {}
    
    for driver_class in selected_drivers:
        if driver_class not in driver_counts:
            driver_counts[driver_class] = 0
        driver_counts[driver_class] += 1
        
        instance_num = driver_counts[driver_class]
        driver_class_name, driver_config = create_driver_skeleton(driver_class, instance_num)
        
        driver_entry = {driver_class_name: driver_config}
        driver_list.append(driver_entry)
        print(f"  • Generated skeleton for '{driver_config['name']}' ({driver_class})")
    
    return driver_list

def planner_main(args: argparse.Namespace) -> int:
    """Main function for the planner command"""
    # Ensure config file has .yaml extension
    args.config_file = ensure_yaml_extension(args.config_file)
    
    config_path = Path(args.config_file)
    
    print("Labgrid Environment Planner")
    print("Interactive tool to create labgrid environment configurations\n")
    
    # Load existing config if editing or file exists
    if args.edit or config_path.exists():
        if config_path.exists():
            print(f"Loading existing configuration from {args.config_file}")
            yaml_config = load_existing_config(args.config_file)
        else:
            print(f"Configuration file {args.config_file} not found")
            yaml_config = {}
    else:
        yaml_config = {}
    
    try:
        if args.edit and yaml_config:
            # Show existing targets
            print("Existing targets:")
            for target_name in yaml_config.keys():
                print(f"  • {target_name}")
            
            target_name = input("\nTarget to edit (or new target name): ").strip()
        else:
            # Create new configuration
            target_name = input("Target name (environment identifier) [target]: ").strip()
            if not target_name:
                target_name = "target"
        
        # Set location if not exists or if new target
        if target_name not in yaml_config or 'location' not in yaml_config.get(target_name, {}):
            location = input("Location (coordinator location) [local]: ").strip()
            if not location:
                location = "local"
            if target_name not in yaml_config:
                yaml_config[target_name] = {}
            yaml_config[target_name]['location'] = location
        
        # Resource selection phase
        print("\nStarting resource selection interface...")
        
        try:
            selected_resources = curses.wrapper(lambda stdscr: ResourceSelector(stdscr, "resources").run())
        except KeyboardInterrupt:
            print("\nOperation cancelled")
            return 1
        
        if not selected_resources:
            print("No resources selected.")
            selected_resources = []
        else:
            print(f"\nSelected {len(selected_resources)} resource types:")
            for resource in selected_resources:
                print(f"  • {resource}")
        
        # Driver selection phase
        print("\nStarting driver selection interface...")
        
        try:
            selected_drivers = curses.wrapper(lambda stdscr: ResourceSelector(stdscr, "drivers").run())
        except KeyboardInterrupt:
            print("\nOperation cancelled")
            return 1
        
        if not selected_drivers:
            print("No drivers selected.")
            selected_drivers = []
        else:
            print(f"\nSelected {len(selected_drivers)} driver types:")
            for driver in selected_drivers:
                print(f"  • {driver}")
        
        if not selected_resources and not selected_drivers:
            print("No resources or drivers selected. Nothing to generate.")
            return 0
        
        # Configuration phase - generate skeletons
        yaml_config[target_name] = {"location": yaml_config[target_name]["location"]}
        
        if selected_resources:
            resource_configs = configure_resource_instances(selected_resources)
            yaml_config[target_name].update(resource_configs)
        
        # Generate YAML for resources
        if selected_resources:
            yaml_output = generate_yaml(target_name, yaml_config[target_name]['location'], 
                                      selected_resources, [], is_driver_file=False)
        else:
            # If no resources, create minimal config with just location
            config = {target_name: {"location": yaml_config[target_name]["location"]}}
            yaml_output = yaml.dump(config, default_flow_style=False, indent=2)
        
        # Save main configuration
        try:
            with open(args.config_file, 'w') as f:
                f.write(yaml_output)
            print(f"Configuration saved to {args.config_file}")
        except Exception as e:
            print(f"Error saving configuration: {e}")
        
        # Save driver configuration to separate file if drivers were selected
        if selected_drivers:
            driver_filename = get_driver_filename(args.config_file)
            driver_yaml_output = generate_yaml(target_name, "", 
                                             [], selected_drivers, is_driver_file=True)
            try:
                with open(driver_filename, 'w') as f:
                    f.write(driver_yaml_output)
                print(f"Driver configuration saved to {driver_filename}")
            except Exception as e:
                print(f"Error saving driver configuration: {e}")
        
        # Show final configuration
        print(f"\nGenerated configuration:")
        print("=" * 60)
        print(yaml_output)
        print("=" * 60)
        
        print(f"\nNext steps:")
        print(f"1. Edit the generated configuration file: {args.config_file}")
        if selected_drivers:
            print(f"2. Edit the generated driver configuration file: {get_driver_filename(args.config_file)}")
        print("3. Replace all 'CHANGEME' placeholders with actual values")
        print("4. Remove any properties you don't need")
        print("5. Use with labgrid: labgrid-client -c <config> ...")
        
        return 0
        
    except KeyboardInterrupt:
        print("\nOperation cancelled")
        return 1
    except Exception as e:
        print(f"\nError: {e}")
        return 1

def add_planner_subcommand(subparsers):
    """Add the planner subcommand to labgrid's argument parser"""
    parser = subparsers.add_parser(
        'planner',
        help='interactively plan environment configurations',
        description='Interactive tool to create and edit labgrid environment configurations'
    )
    
    parser.add_argument(
        'config_file',
        nargs='?',
        default='environment.yaml',
        help='Configuration file path (default: environment.yaml)'
    )
    
    parser.add_argument(
        '--config', '-c',
        dest='config_file',
        help='Configuration file path (alternative to positional argument)'
    )
    
    parser.add_argument(
        '--edit', '-e',
        action='store_true',
        help='Edit existing configuration file'
    )
    
    parser.set_defaults(func=planner_main)

# For standalone usage (development/testing)
def main():
    """Standalone entry point for development"""
    parser = argparse.ArgumentParser(
        prog='labgrid-planner',
        description='Interactive labgrid environment configuration planner'
    )
    
    parser.add_argument(
        'config_file',
        nargs='?',
        default='environment.yaml',
        help='Configuration file path (default: environment.yaml)'
    )
    
    parser.add_argument(
        '--config', '-c',
        dest='config_file',
        help='Configuration file path (alternative to positional argument)'
    )
    
    parser.add_argument(
        '--edit', '-e',
        action='store_true',
        help='Edit existing configuration file'
    )
    
    args = parser.parse_args()
    return planner_main(args)

if __name__ == '__main__':
    sys.exit(main())

# Integration patch for labgrid/main.py
"""
To integrate this into labgrid, add the following to labgrid/main.py:

1. Import the planner module:
   from .planner import add_planner_subcommand

2. In the main() function, after creating subparsers, add:
   add_planner_subcommand(subparsers)

Example integration:
```python
def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', help='available subcommands')
    
    # Existing subcommands...
    add_client_subcommand(subparsers)
    add_coordinator_subcommand(subparsers)
    
    # Add the planner subcommand
    add_planner_subcommand(subparsers)
    
    args = parser.parse_args()
    if args.func:
        return args.func(args)
```
"""

# Setup instructions for adding to existing labgrid project
"""
## Integration Instructions

1. Copy labgrid/planner.py to the labgrid source directory
2. Add dependencies to setup.py or pyproject.toml:
   - PyYAML>=6.0 (likely already present)

3. Modify labgrid/main.py to import and register the planner subcommand:
   ```python
   from .planner import add_planner_subcommand
   
   # In main():
   add_planner_subcommand(subparsers)
   ```

4. Usage will then be:
   ```bash
   labgrid planner                    # Create new environment
   labgrid planner --edit            # Edit existing environment  
   labgrid planner -c my-env.yaml    # Use custom config file
   ```

The tool provides a curses-based TUI for resource selection followed by
command-line configuration of each selected resource type.
"""
