#!/usr/bin/env python3
"""
Peloton TCX to TrainerRoad TCX Converter

This script converts TCX files exported from Peloton into a format
that is properly readable by TrainerRoad and other training platforms.

Key transformations:
- Removes Creator element
- Fixes namespace usage for extension elements
- Removes Resistance data
- Converts float values to integers where appropriate
- Recalculates speed based on distance deltas
- Removes lap-level aggregate statistics
- Formats with proper XML structure
"""

import xml.etree.ElementTree as ET
from datetime import datetime
import sys
import argparse


def parse_time(time_str):
    """Parse ISO 8601 time string to datetime object."""
    return datetime.fromisoformat(time_str.replace('Z', '+00:00'))


def calculate_speed(prev_distance, curr_distance, prev_time, curr_time):
    """
    Calculate instantaneous speed in meters per second.

    Args:
        prev_distance: Previous distance in meters
        curr_distance: Current distance in meters
        prev_time: Previous timestamp string
        curr_time: Current timestamp string

    Returns:
        Speed in meters per second
    """
    if prev_time is None:
        return 0  # First trackpoint has no speed

    time_delta = (parse_time(curr_time) - parse_time(prev_time)).total_seconds()

    if time_delta == 0:
        return 0

    distance_delta = curr_distance - prev_distance
    return distance_delta / time_delta


def clean_value(value, as_int=False):
    """
    Clean numeric values.

    Args:
        value: String value to clean
        as_int: If True, convert to integer

    Returns:
        Cleaned value as string
    """
    if value is None:
        return None

    try:
        num = float(value)
        if as_int:
            return str(int(round(num)))
        else:
            return str(num)
    except (ValueError, TypeError):
        return value


def process_element(elem, ns):
    """Process XML element to fix namespaces and values."""
    # Create namespace URIs
    tcx_ns = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
    ext_ns = "http://www.garmin.com/xmlschemas/ActivityExtension/v2"

    tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

    # Process based on element type
    if tag_name == 'Value' and elem.text:
        parent_tag = elem.getparent().tag if hasattr(elem, 'getparent') else None
        # Convert heart rate and watts to integers
        elem.text = clean_value(elem.text, as_int=True)
    elif tag_name == 'Cadence' and elem.text:
        elem.text = clean_value(elem.text, as_int=True)

    # Recursively process children
    for child in elem:
        process_element(child, ns)


def convert_tcx_string(input_file, output_file):
    """
    Convert Peloton TCX to TrainerRoad-compatible TCX format using string manipulation.

    This approach uses string replacement for better namespace control.
    """
    # Read the input file
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse to get data for speed calculation
    tree = ET.fromstring(content)

    ns = {
        'tcx': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2',
        'ns3': 'http://www.garmin.com/xmlschemas/ActivityExtension/v2'
    }

    # Build a speed lookup table
    speed_data = {}

    for activity in tree.findall('.//{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Activity'):
        for lap in activity.findall('.//{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Lap'):
            track = lap.find('.//{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Track')
            if track is None:
                continue

            trackpoints = track.findall('.//{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Trackpoint')
            prev_distance = 0
            prev_time = None

            for i, tp in enumerate(trackpoints):
                time_elem = tp.find('.//{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Time')
                dist_elem = tp.find('.//{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}DistanceMeters')

                if time_elem is None or dist_elem is None:
                    continue

                curr_time = time_elem.text
                curr_distance = float(dist_elem.text)

                speed = calculate_speed(prev_distance, curr_distance, prev_time, curr_time)
                speed_data[curr_time] = speed

                prev_distance = curr_distance
                prev_time = curr_time

    # String replacements for namespace fixes
    # Remove Creator element
    import re
    content = re.sub(r'<Creator>.*?</Creator>', '', content, flags=re.DOTALL)

    # Remove Lap Extensions
    content = re.sub(
        r'<Extensions>\s*<TPX[^>]*>.*?</TPX>\s*</Extensions>\s*(?=<Track>)',
        '',
        content,
        flags=re.DOTALL
    )

    # Fix TPX namespace - remove inline xmlns and use ns3 prefix
    content = re.sub(
        r'<TPX xmlns="http://www\.garmin\.com/xmlschemas/ActivityExtension/v2">',
        '<ns3:TPX>',
        content
    )
    content = content.replace('</TPX>', '</ns3:TPX>')

    # Fix Speed tags
    content = content.replace('<Speed>', '<ns3:Speed>')
    content = content.replace('</Speed>', '</ns3:Speed>')

    # Fix Watts tags
    content = content.replace('<Watts>', '<ns3:Watts>')
    content = content.replace('</Watts>', '</ns3:Watts>')

    # Remove Resistance tags
    content = re.sub(r'<Resistance>.*?</Resistance>', '', content)

    # Clean up float values in Value tags (for HR)
    content = re.sub(r'<Value>(\d+)\.0</Value>', r'<Value>\1</Value>', content)

    # Clean up Cadence float values
    content = re.sub(r'<Cadence>(\d+)\.0</Cadence>', r'<Cadence>\1</Cadence>', content)

    # Clean up Watts float values
    content = re.sub(r'<ns3:Watts>(\d+)\.0</ns3:Watts>', r'<ns3:Watts>\1</ns3:Watts>', content)

    # Now rebuild with updated speeds
    for time_str, speed in speed_data.items():
        # Find and replace speed values for this timestamp
        pattern = rf'(<Time>{re.escape(time_str)}</Time>.*?<ns3:Speed>)[\d.]+(<)'
        replacement = rf'\g<1>{speed}\g<2>'
        content = re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)

    # Pretty print using ElementTree
    try:
        root = ET.fromstring(content)
        indent_xml(root)

        # Create proper XML with namespace declarations
        output_content = ET.tostring(root, encoding='unicode')

        # Fix the declaration
        output_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + output_content

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output_content)

    except Exception as e:
        # If pretty printing fails, just write the content as-is
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)

    print(f"Conversion complete: {input_file} -> {output_file}")


def indent_xml(elem, level=0):
    """
    Add indentation to XML for pretty printing.
    """
    indent = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent
        for child in elem:
            indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = indent
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Convert Peloton TCX files to TrainerRoad-compatible format',
        epilog='Example: python convert_tcx.py peloton_ride.tcx converted_ride.tcx'
    )
    parser.add_argument('input_file', help='Input TCX file (Peloton format)')
    parser.add_argument('output_file', help='Output TCX file (TrainerRoad format)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    try:
        convert_tcx_string(args.input_file, args.output_file)
        if args.verbose:
            print("Transformation details:")
            print("  - Removed Creator element")
            print("  - Fixed namespace prefixes (TPX, Speed, Watts)")
            print("  - Removed Resistance data")
            print("  - Converted float values to integers")
            print("  - Recalculated speeds")
            print("  - Removed lap-level aggregate statistics")
    except FileNotFoundError:
        print(f"Error: Input file '{args.input_file}' not found")
        sys.exit(1)
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
