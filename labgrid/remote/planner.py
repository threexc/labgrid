# labgrid/planner.py
"""Interactive environment configuration generator for labgrid"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    import yaml
except ImportError:
    print("PyYAML is required for the plan command. Install with: pip install PyYAML")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich import print as rprint
except ImportError:
    print("Rich is required for the plan command. Install with: pip install rich")
    sys.exit(1)

# Labgrid resource definitions based on actual labgrid resources
LABGRID_RESOURCES = {
    # GPIO Resources
    "SysfsGPIO": {
        "description": "GPIO pin accessed through sysfs",
        "properties": {
            "index": {"type": "int", "description": "GPIO pin number", "required": True}
        }
    },
    "MatchedSysfsGPIO": {
        "description": "GPIO pin accessed through sysfs with device matching",
        "properties": {
            "match": {"type": "dict", "description": "Device matching criteria", "required": True},
            "index": {"type": "int", "description": "GPIO pin number", "required": True}
        }
    },
    
    # Serial Resources  
    "SerialPort": {
        "description": "Generic serial port device",
        "properties": {
            "port": {"type": "str", "description": "Serial port path (e.g., /dev/ttyUSB0)", "required": True},
            "speed": {"type": "int", "description": "Baud rate (default: 115200)", "required": False}
        }
    },
    "USBSerialPort": {
        "description": "USB serial port device with device matching",
        "properties": {
            "match": {"type": "dict", "description": "Device matching criteria", "required": True},
            "speed": {"type": "int", "description": "Baud rate (default: 115200)", "required": False}
        }
    },
    "RawSerialPort": {
        "description": "Raw serial port without higher-level protocols",
        "properties": {
            "port": {"type": "str", "description": "Serial port path", "required": True},
            "speed": {"type": "int", "description": "Baud rate", "required": False}
        }
    },
    
    # Network Resources
    "NetworkInterface": {
        "description": "Network interface for network-based testing",
        "properties": {
            "ifname": {"type": "str", "description": "Network interface name (e.g., eth0)", "required": True},
            "address": {"type": "str", "description": "IP address or hostname", "required": False}
        }
    },
    "USBEthernetPort": {
        "description": "USB Ethernet adapter with device matching",
        "properties": {
            "match": {"type": "dict", "description": "Device matching criteria", "required": True}
        }
    },
    
    # Power Resources
    "ManualPowerPort": {
        "description": "Manually controlled power port",
        "properties": {}
    },
    "ExternalPowerPort": {
        "description": "External power control via command execution",
        "properties": {
            "cmd_on": {"type": "str", "description": "Command to turn power on", "required": True},
            "cmd_off": {"type": "str", "description": "Command to turn power off", "required": True},
            "cmd_cycle": {"type": "str", "description": "Command to cycle power", "required": False}
        }
    },
    "NetworkPowerPort": {
        "description": "Network-controlled power port",
        "properties": {
            "host": {"type": "str", "description": "Hostname or IP address", "required": True},
            "index": {"type": "int", "description": "Port index", "required": True}
        }
    },
    "USBPowerPort": {
        "description": "USB power control port",
        "properties": {
            "match": {"type": "dict", "description": "Device matching criteria", "required": True},
            "index": {"type": "int", "description": "Port index", "required": True}
        }
    },
    "HttpDigitalOutput": {
        "description": "Digital output controlled via HTTP",
        "properties": {
            "url": {"type": "str", "description": "Base URL for HTTP requests", "required": True},
            "index": {"type": "int", "description": "Output index/channel", "required": True}
        }
    },
    
    # Storage Resources
    "USBMassStorage": {
        "description": "USB mass storage device",
        "properties": {
            "match": {"type": "dict", "description": "Device matching criteria", "required": True}
        }
    },
    "NetworkMassStorage": {
        "description": "Network-attached mass storage",
        "properties": {
            "host": {"type": "str", "description": "Hostname or IP address", "required": True},
            "rootpath": {"type": "str", "description": "Root path on the storage", "required": False}
        }
    },
    
    # Android/Mobile Resources
    "AndroidFastboot": {
        "description": "Android fastboot interface",
        "properties": {
            "match": {"type": "dict", "description": "Device matching criteria", "required": True}
        }
    },
    "USBADBDevice": {
        "description": "Android ADB device",
        "properties": {
            "match": {"type": "dict", "description": "Device matching criteria", "required": True}
        }
    },
    "AndroidUSBFastboot": {
        "description": "Android USB fastboot device",
        "properties": {
            "match": {"type": "dict", "description": "Device matching criteria", "required": True}
        }
    },
    
    # Bootloader Resources
    "UBootDriver": {
        "description": "U-Boot bootloader interface",
        "properties": {
            "prompt": {"type": "str", "description": "U-Boot prompt pattern", "required": False},
            "autoboot": {"type": "str", "description": "Autoboot key sequence", "required": False}
        }
    },
    "BareboxDriver": {
        "description": "Barebox bootloader interface", 
        "properties": {
            "prompt": {"type": "str", "description": "Barebox prompt pattern", "required": False}
        }
    },
    
    # Remote Resources
    "RemotePlace": {
        "description": "Remote place for distributed testing",
        "properties": {
            "name": {"type": "str", "description": "Remote place name", "required": True}
        }
    },
    "NetworkService": {
        "description": "Network service endpoint",
        "properties": {
            "address": {"type": "str", "description": "Service address", "required": True},
            "username": {"type": "str", "description": "Username for authentication", "required": False}
        }
    },
    
    # Video/Display Resources
    "USBVideo": {
        "description": "USB video capture device",
        "properties": {
            "match": {"type": "dict", "description": "Device matching criteria", "required": True}
        }
    },
    
    # Test Equipment Resources
    "NetworkSigrokDevice": {
        "description": "Network-connected Sigrok-compatible device",
        "properties": {
            "host": {"type": "str", "description": "Hostname or IP address", "required": True},
            "device": {"type": "str", "description": "Device identifier", "required": True}
        }
    },
    "USBSigrokDevice": {
        "description": "USB-connected Sigrok-compatible device",
        "properties": {
            "match": {"type": "dict", "description": "Device matching criteria", "required": True},
            "driver": {"type": "str", "description": "Sigrok driver name", "required": True}
        }
    }
}

console = Console()

def get_resource_classes() -> List[str]:
    """Get list of available resource classes"""
    return sorted(LABGRID_RESOURCES.keys())

def get_resource_properties(resource_class: str) -> Dict[str, Any]:
    """Get properties for a specific resource class"""
    return LABGRID_RESOURCES.get(resource_class, {}).get("properties", {})

def get_resource_description(resource_class: str) -> str:
    """Get description for a specific resource class"""
    return LABGRID_RESOURCES.get(resource_class, {}).get("description", "")

def load_existing_config(filepath: str) -> Dict[str, Any]:
    """Load existing YAML configuration file"""
    try:
        with open(filepath, 'r') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except yaml.YAMLError as e:
        console.print(f"[red]Error parsing YAML file: {e}[/red]")
        return {}

def save_config(config: Dict[str, Any], filepath: str) -> None:
    """Save configuration to YAML file"""
    try:
        with open(filepath, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        console.print(f"[green]Configuration saved to {filepath}[/green]")
    except Exception as e:
        console.print(f"[red]Error saving configuration: {e}[/red]")

def prompt_for_match_criteria() -> Dict[str, str]:
    """Prompt user for device matching criteria"""
    match_dict = {}
    console.print("\n[cyan]Device matching criteria:[/cyan]")
    
    common_keys = [
        "@SUBSYSTEM", "@ID_SERIAL_SHORT", "@ID_VENDOR_ID", "@ID_MODEL_ID", 
        "@DEVNAME", "@ID_PATH", "@ID_USB_INTERFACE_NUM", "@DEVPATH"
    ]
    
    console.print("[dim]Common matching keys: " + ", ".join(common_keys) + "[/dim]")
    console.print("[dim]Example: @SUBSYSTEM=usb, @ID_SERIAL_SHORT=ABC123[/dim]")
    console.print("[dim]Press Enter with empty key to finish[/dim]")
    
    while True:
        key = Prompt.ask("Match key (e.g., @SUBSYSTEM)", default="")
        if not key.strip():  # If empty or just whitespace
            break
            
        value = Prompt.ask(f"Value for {key}")
        if value.strip():  # Only add if value is not empty
            match_dict[key] = value
        
        # Ask if they want to add another match criterion
        if not Confirm.ask("Add another match criterion?", default=False):
            break
    
    return match_dict

def prompt_for_property_value(prop_name: str, prop_info: Dict[str, Any]) -> Any:
    """Prompt user for a property value based on its type"""
    prop_type = prop_info.get("type", "str")
    description = prop_info.get("description", "")
    
    prompt_text = f"{prop_name}"
    if description:
        prompt_text += f" ({description})"
    
    if prop_type == "dict" and prop_name == "match":
        return prompt_for_match_criteria()
    elif prop_type == "int":
        while True:
            try:
                value = Prompt.ask(prompt_text)
                return int(value) if value else None
            except ValueError:
                console.print("[red]Please enter a valid integer[/red]")
    else:
        return Prompt.ask(prompt_text)

def select_resource_class() -> Optional[str]:
    """Allow user to select a single resource class (for edit mode)"""
    classes = get_resource_classes()
    
    # Display available classes in a table
    table = Table(title="Available Labgrid Resource Classes")
    table.add_column("Index", style="cyan")
    table.add_column("Class Name", style="green")
    table.add_column("Description", style="dim")
    
    for i, cls in enumerate(classes, 1):
        description = get_resource_description(cls)
        table.add_row(str(i), cls, description)
    
    console.print(table)
    
    while True:
        try:
            choice = Prompt.ask("\nSelect resource class by number")
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(classes):
                    return classes[idx]
            console.print("[red]Invalid selection. Please enter a valid number.[/red]")
        except KeyboardInterrupt:
            return None

def configure_resource() -> Dict[str, Any]:
    """Configure a single resource (legacy function for compatibility)"""
    return select_and_configure_single_resource()

def select_resource_types() -> List[str]:
    """Multi-select interface for choosing resource types to configure"""
    classes = get_resource_classes()
    
    # Group classes by category for better organization
    categories = {
        "GPIO": [c for c in classes if "GPIO" in c],
        "Serial": [c for c in classes if "Serial" in c or c == "RawSerialPort"],
        "Network": [c for c in classes if "Network" in c or "Ethernet" in c],
        "Power": [c for c in classes if "Power" in c or "DigitalOutput" in c or c == "ManualPowerPort"],
        "Storage": [c for c in classes if "Storage" in c],
        "Android/Mobile": [c for c in classes if "Android" in c or "ADB" in c],
        "Bootloader": [c for c in classes if "Driver" in c],
        "Video": [c for c in classes if "Video" in c],
        "Test Equipment": [c for c in classes if "Sigrok" in c],
        "Other": []
    }
    
    # Add remaining classes to "Other"
    all_categorized = sum(categories.values(), [])
    categories["Other"] = [c for c in classes if c not in all_categorized]
    
    console.print("\n[bold cyan]Resource Type Selection Menu[/bold cyan]")
    console.print("[dim]Select the types of resources you want to configure for this environment[/dim]\n")
    
    selected_resources = []
    
    for category, class_list in categories.items():
        if not class_list:
            continue
            
        console.print(f"\n[yellow]── {category} Resources ──[/yellow]")
        
        for resource_class in class_list:
            description = get_resource_description(resource_class)
            
            # Show resource info
            console.print(f"\n[green]{resource_class}[/green]")
            console.print(f"[dim]  {description}[/dim]")
            
            # Ask if user wants this resource type
            if Confirm.ask(f"  Include {resource_class}?", default=False):
                selected_resources.append(resource_class)
    
    return selected_resources

def configure_resource_instance(resource_class: str, instance_num: int) -> Dict[str, Any]:
    """Configure a single instance of a resource type"""
    console.print(f"\n[green]Configuring {resource_class} #{instance_num}[/green]")
    console.print(f"[dim]{get_resource_description(resource_class)}[/dim]")
    
    properties = get_resource_properties(resource_class)
    resource_config = {"cls": resource_class}
    
    if not properties:
        console.print("[yellow]This resource has no configurable properties.[/yellow]")
        return resource_config
    
    # Show available properties
    console.print(f"\n[cyan]Properties for {resource_class}:[/cyan]")
    for prop_name, prop_info in properties.items():
        required = prop_info.get("required", False)
        description = prop_info.get("description", "")
        req_text = "[red](required)[/red]" if required else "[dim](optional)[/dim]"
        console.print(f"  • {prop_name}: {description} {req_text}")
    
    # Configure each property
    for prop_name, prop_info in properties.items():
        required = prop_info.get("required", False)
        
        if required or Confirm.ask(f"\nConfigure {prop_name}?", default=True):
            value = prompt_for_property_value(prop_name, prop_info)
            if value is not None and value != "":
                resource_config[prop_name] = value
    
    return resource_config

def add_resources_to_target(config: Dict[str, Any], target_name: str, is_new_config: bool = False) -> None:
    """Add resources to a target configuration"""
    if target_name not in config:
        config[target_name] = {}
    
    target_config = config[target_name]
    
    if is_new_config:
        # For new configs, use the menuconfig-style selection
        selected_resource_types = select_resource_types()
        
        if not selected_resource_types:
            console.print("[yellow]No resource types selected.[/yellow]")
            return
        
        console.print(f"\n[bold green]Selected resource types:[/bold green]")
        for resource_type in selected_resource_types:
            console.print(f"  • {resource_type}")
        
        # Configure each selected resource type
        for resource_class in selected_resource_types:
            console.print(f"\n[bold blue]═══ Configuring {resource_class} instances ═══[/bold blue]")
            
            instance_count = 1
            while True:
                # Configure this instance
                resource_config = configure_resource_instance(resource_class, instance_count)
                
                if resource_config:
                    # Generate a default label or ask for one
                    default_label = f"{resource_class.lower().replace('matched', '').replace('usb', '').replace('sysfs', '')}-{instance_count}"
                    resource_label = Prompt.ask(f"Label for this {resource_class}", default=default_label)
                    
                    target_config[resource_label] = resource_config
                    console.print(f"[green]Added '{resource_label}' ({resource_class})[/green]")
                
                # Ask if they want another instance of this resource type
                if not Confirm.ask(f"\nAdd another {resource_class} instance?", default=False):
                    break
                
                instance_count += 1
    else:
        # For editing existing configs, use the old interface
        while True:
            if not Confirm.ask("\nAdd a new resource?", default=True):
                break
            
            resource_label = Prompt.ask("Resource label (e.g., power-gpio, debug-serial)")
            if not resource_label:
                continue
                
            resource_config = select_and_configure_single_resource()
            if resource_config:
                target_config[resource_label] = resource_config
                console.print(f"[green]Added resource '{resource_label}'[/green]")

def select_and_configure_single_resource() -> Dict[str, Any]:
    """Select and configure a single resource (for edit mode)"""
    resource_class = select_resource_class()
    if not resource_class:
        return {}
    
    return configure_resource_instance(resource_class, 1)

def planner_main(args: argparse.Namespace) -> int:
    """Main function for the planner command"""
    console.print("[bold blue]Labgrid Environment Planner[/bold blue]")
    console.print("[dim]Interactive tool to create labgrid environment configurations[/dim]\n")
    
    config_path = Path(args.config)
    
    # Load existing config if editing or file exists
    if args.edit or config_path.exists():
        if config_path.exists():
            console.print(f"[yellow]Loading existing configuration from {args.config}[/yellow]")
            yaml_config = load_existing_config(args.config)
        else:
            console.print(f"[red]Configuration file {args.config} not found[/red]")
            yaml_config = {}
    else:
        yaml_config = {}
    
    try:
        if args.edit and yaml_config:
            # Show existing targets
            console.print("[cyan]Existing targets:[/cyan]")
            for target_name in yaml_config.keys():
                console.print(f"  • {target_name}")
            
            target_name = Prompt.ask("\nTarget to edit (or new target name)")
        else:
            # Create new configuration
            target_name = Prompt.ask("Target name (environment identifier)", default="target")
        
        # Set location if not exists or if new target
        if target_name not in yaml_config or 'location' not in yaml_config.get(target_name, {}):
            location = Prompt.ask("Location (coordinator location)", default="local")
            if target_name not in yaml_config:
                yaml_config[target_name] = {}
            yaml_config[target_name]['location'] = location
        
        # Add resources
        is_new_config = not args.edit and not config_path.exists()
        add_resources_to_target(yaml_config, target_name, is_new_config)
        
        # Save configuration
        save_config(yaml_config, args.config)
        
        # Show final configuration
        console.print(f"\n[bold green]Final configuration:[/bold green]")
        console.print(yaml.dump(yaml_config, default_flow_style=False, indent=2))
        
        console.print(f"\n[bold cyan]Next steps:[/bold cyan]")
        console.print(f"1. Review the generated configuration: {args.config}")
        console.print("2. Add any additional manual configuration as needed")
        console.print("3. Use with labgrid: labgrid-client -c <config> ...")
        
        return 0
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled[/yellow]")
        return 1
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        return 1

def add_planner_subcommand(subparsers):
    """Add the planner subcommand to labgrid's argument parser"""
    parser = subparsers.add_parser(
        'planner',
        help='interactively plan environment configurations',
        description='Interactive tool to create and edit labgrid environment configurations'
    )
    
    parser.add_argument(
        '--config', '-c',
        default='environment.yaml',
        help='Configuration file path (default: environment.yaml)'
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
        '--config', '-c',
        default='environment.yaml',
        help='Configuration file path (default: environment.yaml)'
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
