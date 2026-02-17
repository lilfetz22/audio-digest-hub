# Audio Digest Hub

An intelligent system that automatically converts your email newsletters into personalized audiobooks using AI text-to-speech technology. Never miss important content from your favorite newsletters - listen to them on the go!

## 🎯 What It Does

Audio Digest Hub transforms your daily email newsletters into high-quality audiobooks by:

1. **Email Processing**: Automatically fetches newsletters from your Gmail inbox
2. **Content Extraction**: Intelligently extracts and cleans newsletter content
3. **AI Voice Synthesis**: Converts text to natural-sounding speech using Kokoro TTS (formerly Coqui)
4. **Smart Organization**: Creates structured audiobooks with chapters for each newsletter
5. **Web Player**: Provides a modern web interface to listen to your audiobooks with progress tracking

## 🏗️ Architecture

### Frontend (React Web App)
- **Framework**: React 18 with TypeScript
- **UI Components**: shadcn/ui with Tailwind CSS
- **State Management**: TanStack Query for server state
- **Authentication**: Supabase Auth
- **Audio Player**: Custom player with chapter navigation and progress tracking

### Backend (Supabase)
- **Database**: PostgreSQL with real-time subscriptions
- **Storage**: File storage for audiobook MP3s
- **Edge Functions**: TypeScript serverless functions for API endpoints
- **Authentication**: Row-level security and API key management

- ### Audio Processing (Python)
- **TTS Engine**: Kokoro TTS (82M parameters) — a compact, fast, and high-quality open-source TTS model
- **Email Integration**: Gmail API for newsletter fetching
- **Audio Processing**: PyDub for MP3 conversion and chunking
- **Smart Scheduling**: Automatic processing with duplicate detection

## 🚀 Getting Started

### Prerequisites

- **Node.js** (v18 or higher) - [Install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating)
- **Python** (3.8 or higher) with pip
- **Gmail Account** with API access enabled
- **Supabase Account** for backend services
- **FFmpeg** (for audio processing) - automatically installed via `imageio-ffmpeg` package, or install system-wide:
  - Windows: `winget install ffmpeg` or `choco install ffmpeg`
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg` (Debian/Ubuntu) or `sudo yum install ffmpeg` (RHEL/CentOS)

### Frontend Setup

1. **Clone and install dependencies**:
   ```bash
   git clone <repository-url>
   cd audio-digest-hub
   npm install
   ```

2. **Start the development server**:
   ```bash
   npm run dev
   ```

3. **Build for production**:
   ```bash
   npm run build
   ```

### Python Audio Processor Setup

1. **Navigate to the audiobooks directory**:
   ```bash
   cd src/audiobooks
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv audiogeneratorenv
   source audiogeneratorenv/bin/activate  # On Windows: audiogeneratorenv\Scripts\activate
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the system**:
   - Copy `config.ini.example` to `config.ini` (if available)
   - Set up Gmail API credentials in `credentials.json`
   - Configure Supabase API URL and service role key
   - Optionally add a reference voice file for custom TTS voice

5. **Run the audio processor or Colab notebook**:
- **Colab (recommended for GPU)**: Open `src/audiobooks/TTS_Generation_Colab.ipynb` in Google Colab and run the notebook for a GPU-accelerated Kokoro TTS workflow.

- **Local**: Use the Python script (CPU/GPU) to process audio locally:
   ```bash
   python generate_audiobook.py
   ```

### Configuration Options

The Python processor supports several command-line options:

```bash
# Process a specific date
python generate_audiobook.py --date 2024-01-15

# Process a date range
python generate_audiobook.py --start-date 2024-01-01 --end-date 2024-01-15

# Auto-detect and process since last upload (default behavior)
python generate_audiobook.py
```

## 🛠️ Technology Stack

### Frontend Technologies
- **React 18** - Modern React with hooks and concurrent features
- **TypeScript** - Type-safe JavaScript development
- **Vite** - Fast build tool and development server
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - High-quality React components
- **Radix UI** - Accessible component primitives
- **TanStack Query** - Powerful data synchronization
- **React Router** - Client-side routing

### Backend Technologies
- **Supabase** - Backend-as-a-Service platform
- **PostgreSQL** - Robust relational database
- **Deno** - Secure TypeScript runtime for edge functions
- **Row Level Security** - Database-level authorization

### AI & Audio Processing
- **Kokoro TTS** - Open-source, small-footprint TTS engine with high quality (24kHz native)
- **PyTorch** - Machine learning framework
- **PyDub / soundfile** - Audio manipulation and I/O utilities
- **Gmail API** - Email integration

### TTS Migration: Coqui → Kokoro
This project migrated its TTS engine from Coqui (XTTS v2) to Kokoro TTS.
- Kokoro provides a smaller, faster, and actively maintained model (approx. 82M parameters).
- Kokoro's native sample rate is 24 kHz; the notebook and pipeline use this by default.
- For GPU-accelerated generation, use the `TTS_Generation_Colab.ipynb` notebook in `src/audiobooks`.

## 📁 Project Structure

```
audio-digest-hub/
├── src/
│   ├── components/          # Reusable React components
│   ├── pages/              # Application pages (Dashboard, Player, Settings)
│   ├── hooks/              # Custom React hooks
│   ├── lib/                # Utility functions
│   ├── integrations/       # Supabase client configuration
│   └── audiobooks/         # Python audio processing system
│       ├── generate_audiobook.py    # Main processing script
│       ├── requirements.txt         # Python dependencies
│       └── config.ini              # Configuration file
├── supabase/
│   ├── functions/          # Edge functions (API endpoints)
│   ├── migrations/         # Database schema migrations
│   └── config.toml         # Supabase configuration
├── public/                 # Static assets
└── package.json           # Node.js dependencies and scripts
```

## 🔧 Key Features

### Intelligent Email Processing
- Automatic Gmail integration with OAuth2
- Smart content extraction and cleaning
- Markdown link removal and text optimization
- Duplicate detection to prevent reprocessing

### Advanced Audio Generation
- High-quality AI voice synthesis
- Custom voice cloning support
- Automatic audio chunking for large content
- Chapter-based organization by newsletter source

### Modern Web Interface
- Responsive design for all devices
- Audio player with chapter navigation
- Progress tracking and resume functionality
- User authentication and personal libraries

### Robust Backend
- Scalable Supabase infrastructure
- Secure API key authentication
- Automatic file storage and management
- Real-time data synchronization

## 🔐 Security & Privacy

- **API Key Authentication**: Secure access to backend services
- **Row Level Security**: Database-level access control
- **Local Processing**: Email content processed locally on your machine
- **Encrypted Storage**: Secure file storage in Supabase
- **OAuth2 Integration**: Secure Gmail access without storing passwords

## 📝 Development

### Running Tests
```bash
# Frontend tests
npm run lint

# Python tests
cd src/audiobooks
python -m pytest
```

### Environment Variables
Create a `.env.local` file for frontend configuration:
```
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

If you encounter any issues or have questions:

1. Check the logs in `audiobook_generator.log` for Python processing issues
2. Verify your Gmail API credentials and Supabase configuration
3. Ensure all dependencies are properly installed
4. Check the browser console for frontend issues

## 🎉 Acknowledgments

- **Kokoro TTS** for providing a compact, fast, and high-quality open-source text-to-speech engine (recommended replacement for Coqui)
- **Coqui TTS** (historical) — originally used in this project
- **Supabase** for the powerful backend-as-a-service platform
- **shadcn/ui** for the beautiful component library
- **Gmail API** for reliable email integration