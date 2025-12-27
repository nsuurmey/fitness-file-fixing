# Peloton TCX to TrainerRoad Converter

This tool converts TCX files exported from Peloton bikes into a format that is properly readable by TrainerRoad and other training platforms.

## Problem

Peloton exports TCX files with formatting and structure that some training platforms (like TrainerRoad) cannot properly parse. This converter fixes those issues.

## Key Transformations

The converter makes the following changes to Peloton TCX files:

1. **Removes Creator element** - Peloton-specific metadata that isn't needed
2. **Fixes namespace prefixes** - Converts inline xmlns declarations to proper namespace prefixes (`ns3:TPX`, `ns3:Speed`, `ns3:Watts`)
3. **Removes Resistance data** - Peloton-specific resistance values that aren't standard TCX
4. **Converts floats to integers** - Heart rate, cadence, and power values are converted from floats (95.0) to integers (95)
5. **Recalculates speed values** - Computes instantaneous speed based on distance deltas
6. **Removes lap-level aggregate statistics** - Strips out summary stats that can confuse some parsers
7. **Pretty-prints the XML** - Formats with proper indentation for readability

## Usage

### Basic Usage

```bash
python3 convert_tcx.py input_file.tcx output_file.tcx
```

### With Verbose Output

```bash
python3 convert_tcx.py input_file.tcx output_file.tcx -v
```

### Example

```bash
python3 convert_tcx.py peloton_ride.tcx trainerroad_ready.tcx
```

## Requirements

- Python 3.7 or higher
- No external dependencies (uses only Python standard library)

## Example Files

The `examples/` directory contains:

- **wrong.tcx** - Original Peloton export format (problematic)
- **correct.tcx** - Properly formatted reference file
- **converted_v2.tcx** - Output from this converter

## Technical Details

### What's Different Between Formats?

**Peloton Format (wrong.tcx):**
```xml
<Creator><Name>Peloton Bike</Name></Creator>
<Extensions>
  <TPX xmlns="http://www.garmin.com/xmlschemas/ActivityExtension/v2">
    <Speed>6.04</Speed>
    <Watts>65.0</Watts>
    <Resistance>65.0</Resistance>
  </TPX>
</Extensions>
```

**TrainerRoad Format (correct.tcx):**
```xml
<Extensions>
  <ns3:TPX>
    <ns3:Speed>0</ns3:Speed>
    <ns3:Watts>65</ns3:Watts>
  </ns3:TPX>
</Extensions>
```

### Speed Calculation

The converter recalculates speed values using instantaneous speed:

```
speed = (current_distance - previous_distance) / time_delta
```

The first trackpoint always has a speed of 0 (no previous point for comparison).

## Troubleshooting

### Import fails in TrainerRoad

- Ensure the converted file has proper namespace declarations
- Check that all float values have been converted to integers for HR/Cadence/Watts
- Verify that Resistance tags have been removed

### File size concerns

TCX files can be large (1MB+) for longer rides. This is normal and the converter handles large files efficiently.

## Contributing

Issues and pull requests welcome! If you encounter a Peloton TCX file that doesn't convert properly, please share a sample.

## License

MIT License - See LICENSE file for details
