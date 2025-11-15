"""
UI Structure and Components Documentation
"""

# Main Window Layout
"""
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  🎵 Audio Generator - Desktop App                                      [_ □ ✕]      │
├──────────────────────┬──────────────────────────────────────────────────────────────┤
│                      │                                                              │
│  📚 Danh sách truyện│  📖 [Story Name] - [Author]                                  │
│  ┌────────────────┐ │  Tổng số: [N] chương                                         │
│  │                │ │  ─────────────────────────────────────────────────────────   │
│  │ 📖 Truyện 1    │ │                                                              │
│  │ 📖 Truyện 2 ◀  │ │  [ ] 📋 Chọn tất cả    🤖 Tạo audio tuần tự (0)             │
│  │ 📖 Truyện 3    │ │  ─────────────────────────────────────────────────────────   │
│  │ 📖 Truyện 4    │ │                                                              │
│  │ 📖 Truyện 5    │ │  ╔═══════════════════════════════════════════════════════╗  │
│  │ ...            │ │  ║ ☐ Chương 1  [Tiêu đề chương]                         ║  │
│  │                │ │  ║ [🎵 TTS] [🤖 Selenium] [🤖 AI] [📁 Upload] [📄 Xem]   ║  │
│  └────────────────┘ │  ║ ⏳ Đang xử lý...                                      ║  │
│                      │  ╚═══════════════════════════════════════════════════════╝  │
│  [🔄 Làm mới]       │                                                              │
│                      │  ╔═══════════════════════════════════════════════════════╗  │
│                      │  ║ ☐ Chương 2  [Tiêu đề chương]    🎵 Có audio         ║  │
│                      │  ║ [🔄 TTS Lại] [🔄 Selenium] [🤖 AI] [📁] [▶️] [📄]     ║  │
│                      │  ║ ✅ Hoàn thành!                                        ║  │
│                      │  ╚═══════════════════════════════════════════════════════╝  │
│                      │                                                              │
│                      │  ╔═══════════════════════════════════════════════════════╗  │
│                      │  ║ ☑ Chương 3  [Tiêu đề chương]                         ║  │
│                      │  ║ [🎵 TTS] [🤖 Selenium] [🤖 AI] [📁 Upload] [📄 Xem]   ║  │
│                      │  ╚═══════════════════════════════════════════════════════╝  │
│                      │                                                              │
│                      │  ...                                                         │
│                      │                                                              │
│                      │  ◀ Trước  |  Trang 1/10  |  Sau ▶                           │
│                      │                                                              │
├──────────────────────┴──────────────────────────────────────────────────────────────┤
│  Sẵn sàng                                                                           │
└─────────────────────────────────────────────────────────────────────────────────────┘
"""

# Batch Processing Dialog
"""
┌─────────────────────────────────────────────────────────────────┐
│  🤖 Tạo Audio Tuần Tự Bằng Selenium                    [✕]      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Chương đã chọn: 5                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Chương 1: Tiêu đề chương 1                              │   │
│  │ Chương 2: Tiêu đề chương 2 [🎵 Có audio cũ]            │   │
│  │ ▶ Chương 3: Tiêu đề chương 3  ◀ (đang xử lý)           │   │
│  │ Chương 4: Tiêu đề chương 4                              │   │
│  │ Chương 5: Tiêu đề chương 5                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Tiến độ: 3/5                                                   │
│  ████████████████░░░░░░░░░░░░░░░░ 60%                          │
│                                                                 │
│  Đang xử lý chương 3/5: Tiêu đề chương 3                       │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ [Chương 1] Đã xóa audio cũ                              │   │
│  │ [Chương 1] Đang bắt đầu tạo audio Selenium...           │   │
│  │ [Chương 1] Task ID: abc123                              │   │
│  │ [Chương 1] Đang xử lý... (10/30)                        │   │
│  │ ✅ Chương 1: Hoàn thành!                                 │   │
│  │                                                             │   │
│  │ [Chương 2] Đã xóa audio cũ                              │   │
│  │ [Chương 2] Đang bắt đầu tạo audio Selenium...           │   │
│  │ ✅ Chương 2: Hoàn thành!                                 │   │
│  │                                                             │   │
│  │ [Chương 3] Đang bắt đầu tạo audio Selenium...           │   │
│  │ [Chương 3] Đang xử lý... (5/30)                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ⚠️ Lưu ý:                                                      │
│  • Quá trình này sẽ tạo audio tuần tự cho tất cả chương đã chọn│
│  • Audio cũ (nếu có) sẽ được xóa và thay thế                   │
│  • Thời gian xử lý: khoảng 2-5 phút mỗi chương                 │
│  • Vui lòng không đóng cửa sổ này trong quá trình xử lý        │
│                                                                 │
│                              [Đang xử lý...] [Hủy]             │
└─────────────────────────────────────────────────────────────────┘
"""

# View Content Dialog
"""
┌─────────────────────────────────────────────────────────────────┐
│  Chương 5: Tiêu đề chương 5                            [✕]      │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Nội dung chương đầy đủ ở đây...                         │   │
│  │                                                             │   │
│  │ Lorem ipsum dolor sit amet, consectetur adipiscing elit.│   │
│  │ Sed do eiusmod tempor incididunt ut labore et dolore    │   │
│  │ magna aliqua. Ut enim ad minim veniam...                │   │
│  │                                                             │   │
│  │ ...                                                         │   │
│  │                                                             │   │
│  │                                                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│                                            [Đóng]               │
└─────────────────────────────────────────────────────────────────┘
"""

# Component Structure
COMPONENTS = {
    'MainWindow': {
        'description': 'Main application window',
        'components': {
            'Left Panel': {
                'StoryListWidget': 'Display list of all stories',
                'RefreshButton': 'Reload stories from API'
            },
            'Right Panel': {
                'StoryInfoLabel': 'Display current story information',
                'BatchControls': {
                    'SelectAllButton': 'Toggle select all chapters',
                    'BatchGenerateButton': 'Start batch audio generation'
                },
                'ChapterScrollArea': {
                    'ChapterWidget[]': 'List of chapter widgets'
                },
                'PaginationControls': {
                    'PrevButton': 'Go to previous page',
                    'PageLabel': 'Current page indicator',
                    'NextButton': 'Go to next page'
                }
            }
        }
    },
    'ChapterWidget': {
        'description': 'Single chapter display and controls',
        'components': {
            'Checkbox': 'Select chapter for batch processing',
            'ChapterBadge': 'Display chapter number',
            'TitleLabel': 'Chapter title',
            'AudioBadge': 'Show if audio exists',
            'ActionButtons': {
                'TTSButton': 'Generate audio with TTS',
                'SeleniumButton': 'Generate audio with Selenium',
                'AIContentButton': 'Regenerate content with AI',
                'UploadButton': 'Upload audio file',
                'PlayButton': 'Play audio (if exists)',
                'ViewButton': 'View chapter content'
            },
            'StatusLabel': 'Display current status/progress'
        }
    },
    'BatchAudioGenerationDialog': {
        'description': 'Dialog for batch processing',
        'components': {
            'ChapterList': 'Display selected chapters',
            'ProgressBar': 'Show overall progress',
            'ProgressLabel': 'Current chapter being processed',
            'StatusText': 'Detailed log of each chapter',
            'WarningLabel': 'Important notes for user',
            'StartButton': 'Begin batch processing',
            'CancelButton': 'Close dialog'
        }
    },
    'AudioGenerationWorker': {
        'description': 'Background thread for audio generation',
        'signals': {
            'progress': 'Emit status messages',
            'finished': 'Emit completion status'
        }
    }
}

# Color Scheme
COLORS = {
    'Primary': '#007bff',    # Blue - for primary actions
    'Success': '#28a745',    # Green - for success states
    'Warning': '#ffc107',    # Yellow - for warnings
    'Danger': '#dc3545',     # Red - for errors
    'Info': '#17a2b8',       # Cyan - for info
    'Light': '#f8f9fa',      # Light gray - backgrounds
    'Dark': '#343a40',       # Dark gray - text
}

# Badge Colors
BADGES = {
    'chapter_number': {'bg': '#007bff', 'fg': 'white'},
    'has_audio': {'bg': '#28a745', 'fg': 'white'},
    'processing': {'bg': '#ffc107', 'fg': 'black'},
    'completed': {'bg': '#28a745', 'fg': 'white'},
    'failed': {'bg': '#dc3545', 'fg': 'white'},
}

# State Management
STATE = {
    'current_story': 'Currently selected story object',
    'chapters_data': 'Paginated chapter data from API',
    'current_page': 'Current pagination page number',
    'chapter_widgets': 'List of ChapterWidget instances',
    'selected_chapters': 'Set of selected chapter IDs for batch',
}

# Threading Model
THREADING = {
    'Main Thread': 'UI rendering and user interaction',
    'AudioGenerationWorker': 'Background audio generation per chapter',
    'Batch Processing': 'Sequential processing in BatchAudioGenerationDialog',
    'API Calls': 'Synchronous requests (could be improved with async)',
}

# Key Features Comparison with StoryDetailScreen.tsx
FEATURE_COMPARISON = {
    'Story Selection': '✅ Both',
    'Chapter List with Pagination': '✅ Both',
    'TTS Audio Generation': '✅ Both',
    'Selenium Audio Generation': '✅ Both',
    'Batch Processing': '✅ Both',
    'Upload Audio': '✅ Both',
    'View Content': '✅ Both',
    'AI Content Generation': '✅ Both',
    'Play Audio': '✅ Both',
    'Task Status Polling': '✅ Both',
    'Progress Indicators': '✅ Both',
    'Add New Chapter': '❌ Desktop (can be added)',
    'Web-based': '✅ React / ❌ Desktop',
    'Offline Support': '❌ Both (require API)',
    'Native OS Integration': '❌ React / ✅ Desktop',
}
