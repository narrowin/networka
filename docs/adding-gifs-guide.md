# Adding Animated GIFs - Guide

This document shows you how to add animated GIFs to showcase Networka features.

## File Structure

Place your GIF files in:
```
docs/assets/gifs/
├── demo.gif              # Main demo for README
├── cli-demo.gif          # CLI demo for docs
├── device-backup.gif     # Feature-specific demos
├── file-upload.gif
└── multi-device.gif
```

## In README.md

```markdown
## Demo

<div align="center">
  <img src="https://raw.githubusercontent.com/narrowin/networka/main/docs/assets/gifs/demo.gif" alt="Networka CLI Demo" width="800"/>
  <p><em>Running commands across multiple network devices with Networka</em></p>
</div>
```

## In Documentation Pages

```markdown
## Feature Demo

<div align="center">
  <img src="../assets/gifs/feature-demo.gif" alt="Feature Demo" width="100%" style="max-width: 800px;"/>
  <p><em>Description of what the GIF demonstrates</em></p>
</div>
```

## Best Practices

### GIF Creation
- **Duration**: Keep GIFs under 30 seconds
- **Size**: Optimize file size (aim for < 5MB)
- **Resolution**: Use 1080p or lower for compatibility
- **Speed**: Consider 1.5x-2x speed for faster demonstrations

### Tools for Creating GIFs
- **asciinema + agg**: Best for terminal recordings
- **LICEcap**: Simple screen recording to GIF
- **ffmpeg**: Convert videos to optimized GIFs

### File Naming
- Use descriptive names: `device-backup-demo.gif`
- Include feature context: `mikrotik-commands.gif`
- Avoid generic names like `demo1.gif`

## Example Terminal Recording Workflow

```bash
# 1. Record terminal session
asciinema rec cli-demo.cast

# 2. Convert to GIF (requires agg)
agg cli-demo.cast cli-demo.gif

# 3. Optimize GIF size if needed
gifsicle -O3 --lossy=80 cli-demo.gif -o cli-demo-optimized.gif
```

## Integration Examples

### In Feature Documentation

Add to `docs/running-commands.md`:
```markdown
## Quick Example

<img src="../assets/gifs/running-commands.gif" alt="Running Commands Demo" width="100%"/>

The above shows executing a command across multiple devices...
```

### In Getting Started Guide

Add to `docs/getting-started.md`:
```markdown
## Installation Demo

<img src="../assets/gifs/installation.gif" alt="Installation Process" width="100%"/>

Follow these steps to install Networka...
```
