# Chess AI Mini Project

Repository: https://github.com/Aj-Shaer07/AI_MINIPROJ.git

## Branches

- `webapp` - Web application branch
- `Flutter-apk` - Flutter mobile/app build branch

## Project Overview

This repository contains a chess AI project with two main delivery paths:

- A web application branch for browser-based play and analysis
- A Flutter branch for mobile and APK builds

## Git Workflow

### Clone the repository

```bash
git clone https://github.com/Aj-Shaer07/AI_MINIPROJ.git
cd AI_MINIPROJ
```

### Check available branches

```bash
git branch -a
```

### Checkout any branch

Use `git checkout <branch-name>` to move between branches at any time.

```bash
git checkout webapp
git checkout Flutter-apk
```

If a branch is only on the remote, fetch it first and create a local tracking branch:

```bash
git fetch origin
git checkout -b webapp origin/webapp
git checkout -b Flutter-apk origin/Flutter-apk
```

### Update your local copy

```bash
git pull origin webapp
git pull origin Flutter-apk
```

### Useful Git commands

```bash
git status
git branch
git log --oneline --max-count=10
```

Use the Git commands above before following the WebApp or Flutter run instructions.

## File Structure

```text
AI_MINIPROJ/
|-- README.md
|-- algorithms/
|   |-- __init__.py
|   |-- evaluation.py
|   |-- main.py
|   |-- move_generation.py
|   |-- move_ordering.py
|   |-- search.py
|   |-- tablebase.py
|   `-- transposition.py
|-- data/
|   `-- syzygy/
|       `-- 3-4-5/
|           |-- checksum.md5
|           |-- KBNvK.rtbw
|           |-- KBNvK.rtbz
|           `-- ...
|-- UI/
|   |-- chessboard.py
|   |-- evaluation_values.py
|   |-- game_controller.py
|   |-- landing.py
|   |-- main.py
|   |-- pieces.py
|   `-- values.py
`-- mindgambit/
    |-- android/
    |-- build/
    |-- ios/
    |-- linux/
    |-- macos/
    `-- windows/
```

## How To Run

### WebApp Branch

Use the `webapp` branch for the browser-based project.

#### Prerequisites

- Python 3.10+
- Node.js 18+
- npm

#### Create a virtual environment

Windows (PowerShell):

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

#### Run the backend

```bash
cd backend
python -m pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend URL:

- http://127.0.0.1:8000

Quick check:

- Open http://127.0.0.1:8000/health

#### Run the frontend

Open a second terminal from the project root:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

- http://localhost:5173

#### Useful WebApp commands

Run the terminal engine game:

```bash
python algorithms/main.py
```

Run the backend health script:

```bash
python backend/scripts/health_check.py
```

Run the frontend build:

```bash
cd frontend
npm run build
```

### Flutter-apk Branch

Use the `Flutter-apk` branch for the Flutter app and APK build.

#### Prerequisites

- Flutter SDK
- Dart SDK
- Android Studio
- Android SDK and platform tools
- VS Code
- Git

#### Open the app folder

```bash
cd mindgambit
```

#### Get dependencies

```bash
flutter pub get
```

#### Run the app

```bash
flutter run
```

#### Run on a specific device

```bash
flutter run -d android
flutter run -d chrome
flutter run -d windows
```

#### Build the APK

```bash
cd mindgambit
flutter build apk --release
```

APK output:

```text
mindgambit/build/app/outputs/flutter-apk/app-release.apk
```

#### Build other targets

```bash
cd mindgambit
flutter build web
flutter build windows
```

## Notes

- If Flutter reports missing Android licenses, run `flutter doctor --android-licenses`.
- If the web branch uses a backend and frontend split, start both services before opening the app.
