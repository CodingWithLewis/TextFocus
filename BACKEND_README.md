# Quick Cuts Backend Service

A Python backend service for the Quick Cuts Electron app that provides image word alignment processing via JSON IPC communication.

## Architecture

The backend service consists of three main components:

1. **`backend_service.py`** - Main IPC service that handles JSON commands via stdin/stdout
2. **`quick_cuts_backend.py`** - Refactored image processing engine with progress callbacks and cancellation
3. **`test_backend.py`** - Test client for validating the backend functionality

## Features

- **JSON IPC Communication** - Communicates with Electron frontend via JSON messages over stdin/stdout
- **Progress Callbacks** - Real-time progress updates during batch processing
- **Graceful Cancellation** - Ability to cancel processing operations mid-execution
- **Structured Results** - Detailed JSON responses with success/failure status and error messages
- **PyInstaller Compatible** - Can be bundled into a standalone executable
- **Subprocess-safe Logging** - Logging configured to avoid conflicts with IPC communication

## Installation

### For Development
```bash
pip install -r requirements-backend.txt
```

### For Production (PyInstaller)
```bash
# Install dependencies
pip install -r requirements-backend.txt

# Build executable
pyinstaller backend_service.spec

# The executable will be in dist/quick_cuts_backend.exe
```

## Usage

### Starting the Service
```bash
python backend_service.py
```

The service will:
1. Send a startup confirmation message
2. Listen for JSON commands on stdin
3. Send responses and progress updates to stdout
4. Log errors and debug info to stderr and `backend_service.log`

### Communication Protocol

All communication uses JSON messages, one per line.

#### Commands

**Process Images**
```json
{
  "command": "process_images",
  "target_word": "example",
  "image_paths": ["/path/to/image1.jpg", "/path/to/image2.png"],
  "output_dir": "/path/to/output",
  "output_size": [1920, 1080],
  "word_height": 100,
  "exact_match": true,
  "background": "dominant",
  "workers": 4
}
```

**Get Status**
```json
{
  "command": "get_status"
}
```

**Cancel Processing**
```json
{
  "command": "cancel_processing"
}
```

**Shutdown**
```json
{
  "command": "shutdown"
}
```

#### Responses

**Startup Confirmation**
```json
{
  "type": "startup",
  "success": true,
  "message": "Backend service ready"
}
```

**Command Response**
```json
{
  "success": true,
  "message": "Processing started",
  "total_images": 10
}
```

**Progress Update**
```json
{
  "type": "progress",
  "status": {
    "is_processing": true,
    "current_image": 3,
    "total_images": 10,
    "current_operation": "Processing image3.jpg",
    "processed_images": ["image1.jpg", "image2.jpg"],
    "failed_images": [],
    "error_message": null
  }
}
```

**Completion**
```json
{
  "type": "completed",
  "status": {
    "is_processing": false,
    "current_image": 10,
    "total_images": 10,
    "processed_images": ["image1.jpg", "image2.jpg", ...],
    "failed_images": [],
    "current_operation": "Processing complete"
  },
  "results": {
    "successful_count": 8,
    "failed_count": 2,
    "successful_images": ["image1.jpg", "image2.jpg", ...],
    "failed_images": ["image9.jpg", "image10.jpg"]
  }
}
```

**Error Response**
```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

## Testing

Run the test suite to verify the backend works correctly:

```bash
python test_backend.py
```

The test suite will:
- Start the backend service
- Test basic commands (get_status, invalid commands)
- Test processing workflow (parameter validation, cancellation)
- Verify proper error handling
- Clean shutdown

## Integration with Electron

### Node.js Integration Example

```javascript
const { spawn } = require('child_process');

class QuickCutsBackend {
  constructor() {
    this.process = null;
    this.messageHandlers = new Map();
  }

  start() {
    this.process = spawn('python', ['backend_service.py'], {
      stdio: ['pipe', 'pipe', 'pipe']
    });

    this.process.stdout.on('data', (data) => {
      const lines = data.toString().split('\n');
      for (const line of lines) {
        if (line.trim()) {
          try {
            const message = JSON.parse(line);
            this.handleMessage(message);
          } catch (e) {
            console.error('Invalid JSON from backend:', line);
          }
        }
      }
    });

    this.process.stderr.on('data', (data) => {
      console.error('Backend stderr:', data.toString());
    });
  }

  sendCommand(command) {
    if (this.process) {
      const json = JSON.stringify(command);
      this.process.stdin.write(json + '\n');
    }
  }

  processImages(options) {
    this.sendCommand({
      command: 'process_images',
      ...options
    });
  }

  getStatus() {
    this.sendCommand({ command: 'get_status' });
  }

  cancelProcessing() {
    this.sendCommand({ command: 'cancel_processing' });
  }

  shutdown() {
    this.sendCommand({ command: 'shutdown' });
  }

  handleMessage(message) {
    // Handle different message types
    switch (message.type) {
      case 'startup':
        console.log('Backend ready');
        break;
      case 'progress':
        this.onProgress(message.status);
        break;
      case 'completed':
        this.onCompleted(message.results);
        break;
      case 'error':
        this.onError(message.error);
        break;
      default:
        this.onResponse(message);
    }
  }

  onProgress(status) {
    // Update UI with progress
  }

  onCompleted(results) {
    // Handle completion
  }

  onError(error) {
    // Handle errors
  }

  onResponse(response) {
    // Handle general responses
  }
}
```

## Error Handling

The backend service includes comprehensive error handling:

- **Input Validation** - All command parameters are validated
- **File System Errors** - Handles missing files, permission issues, Unicode paths
- **OCR Errors** - Graceful handling of Tesseract failures
- **Processing Errors** - Image processing failures are caught and reported
- **Cancellation** - Clean cancellation of ongoing operations
- **Resource Management** - Proper cleanup of threads and processes

## Logging

Logs are written to:
- **`backend_service.log`** - Detailed service logs for debugging
- **stderr** - Real-time logging output (visible in parent process)

The logging is configured to avoid conflicts with the stdin/stdout IPC channel.

## Performance Considerations

- **Sequential Processing** - Images are processed sequentially for reliable progress reporting
- **Memory Management** - Images are processed one at a time to manage memory usage
- **Responsive Cancellation** - Small delays between operations allow for responsive cancellation
- **Worker Threads** - Future enhancement could add true parallel processing

## Dependencies

See `requirements-backend.txt` for the complete list of dependencies required for the backend service.

Key dependencies:
- opencv-python (image processing)
- pytesseract (OCR)
- numpy (array operations)
- scikit-learn (dominant color extraction)
- pyinstaller (executable bundling)

## Troubleshooting

**Backend won't start:**
- Check that Python 3.8+ is installed
- Verify all dependencies are installed
- Ensure Tesseract OCR is installed on the system

**Processing fails:**
- Check that image paths exist and are readable
- Verify output directory is writable
- Check backend_service.log for detailed error messages

**IPC communication issues:**
- Ensure JSON messages are properly formatted
- Check that stdin/stdout are not being used by other processes
- Verify the backend process is still running

**Performance issues:**
- Consider reducing image sizes before processing
- Monitor memory usage during large batch operations
- Check available disk space in output directory