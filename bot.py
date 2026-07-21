
html_code = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nilo Cinema - Watch Movies & TV Series</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --primary: #e50914;
            --primary-dark: #b20710;
            --bg-dark: #0f0f0f;
            --bg-card: #1a1a1a;
            --bg-card-hover: #252525;
            --text-primary: #ffffff;
            --text-secondary: #b3b3b3;
            --text-muted: #666666;
            --border: #2a2a2a;
            --gradient-hero: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            --gradient-overlay: linear-gradient(to top, rgba(15,15,15,1) 0%, rgba(15,15,15,0.8) 30%, rgba(15,15,15,0) 100%);
            --shadow-lg: 0 20px 60px rgba(0,0,0,0.5);
            --shadow-card: 0 8px 32px rgba(0,0,0,0.3);
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 16px;
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: var(--bg-dark);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
        }

        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: var(--bg-dark); }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--primary); }

        .loading-screen {
            position: fixed; inset: 0;
            background: var(--bg-dark);
            display: flex; flex-direction: column;
            align-items: center; justify-content: center;
            z-index: 9999;
            transition: opacity 0.5s, visibility 0.5s;
        }
        .loading-screen.hidden { opacity: 0; visibility: hidden; pointer-events: none; }
        .loading-logo {
            font-size: 3rem; font-weight: 900;
            background: linear-gradient(135deg, var(--primary), #ff6b6b);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            animation: pulse 1.5s ease-in-out infinite;
        }
        .loading-bar {
            width: 200px; height: 3px;
            background: #333; border-radius: 3px;
            margin-top: 20px; overflow: hidden;
        }
        .loading-bar-fill {
            height: 100%; width: 0%;
            background: linear-gradient(90deg, var(--primary), #ff6b6b);
            border-radius: 3px;
            animation: loadBar 2s ease forwards;
        }
        @keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }
        @keyframes loadBar { to { width: 100%; } }

        .navbar {
            position: fixed; top: 0; left: 0; right: 0;
            height: 70px;
            background: rgba(15, 15, 15, 0.95);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border);
            display: flex; align-items: center;
            justify-content: space-between;
            padding: 0 40px;
            z-index: 1000;
            transition: var(--transition);
        }
        .navbar.scrolled {
            background: rgba(15, 15, 15, 0.98);
            box-shadow: 0 4px 30px rgba(0,0,0,0.4);
        }
        .nav-left { display: flex; align-items: center; gap: 40px; }
        .logo {
            font-size: 1.8rem; font-weight: 900;
            background: linear-gradient(135deg, var(--primary), #ff6b6b);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            cursor: pointer; display: flex; align-items: center; gap: 10px;
        }
        .logo i { font-size: 1.5rem; }
        .nav-links { display: flex; gap: 30px; list-style: none; }
        .nav-links a {
            color: var(--text-secondary); text-decoration: none;
            font-weight: 500; font-size: 0.95rem;
            transition: var(--transition);
            position: relative; padding: 5px 0;
        }
        .nav-links a::after {
            content: ''; position: absolute; bottom: 0; left: 0;
            width: 0; height: 2px;
            background: var(--primary);
            transition: var(--transition);
        }
        .nav-links a:hover, .nav-links a.active { color: var(--text-primary); }
        .nav-links a:hover::after, .nav-links a.active::after { width: 100%; }
        .nav-right { display: flex; align-items: center; gap: 20px; }
        .search-box {
            position: relative;
            display: flex; align-items: center;
        }
        .search-box input {
            background: rgba(255,255,255,0.08);
            border: 1px solid var(--border);
            border-radius: 25px;
            padding: 10px 40px 10px 18px;
            color: var(--text-primary);
            width: 250px;
            font-size: 0.9rem;
            transition: var(--transition);
            outline: none;
        }
        .search-box input:focus {
            background: rgba(255,255,255,0.12);
            border-color: var(--primary);
            width: 300px;
        }
        .search-box input::placeholder { color: var(--text-muted); }
        .search-box button {
            position: absolute; right: 12px;
            background: none; border: none;
            color: var(--text-secondary);
            cursor: pointer; font-size: 1rem;
        }
        .nav-icon {
            width: 40px; height: 40px;
            border-radius: 50%;
            background: rgba(255,255,255,0.08);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            display: flex; align-items: center; justify-content: center;
            cursor: pointer;
            transition: var(--transition);
        }
        .nav-icon:hover {
            background: var(--primary);
            color: white; border-color: var(--primary);
        }
        .mobile-menu-btn {
            display: none;
            background: none; border: none;
            color: var(--text-primary);
            font-size: 1.5rem; cursor: pointer;
        }

        .hero {
            position: relative;
            height: 85vh;
            min-height: 600px;
            display: flex; align-items: flex-end;
            padding: 0 60px 80px;
            overflow: hidden;
            margin-top: 70px;
        }
        .hero-bg {
            position: absolute; inset: 0;
            background-size: cover;
            background-position: center;
            transition: opacity 0.8s ease;
        }
        .hero-bg::after {
            content: '';
            position: absolute; inset: 0;
            background: var(--gradient-overlay);
        }
        .hero-content {
            position: relative; z-index: 2;
            max-width: 700px;
            animation: fadeInUp 1s ease;
        }
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(40px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .hero-badge {
            display: inline-flex; align-items: center; gap: 8px;
            background: rgba(229, 9, 20, 0.2);
            border: 1px solid rgba(229, 9, 20, 0.4);
            color: var(--primary);
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 0.8rem; font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 20px;
        }
        .hero-title {
            font-size: 3.5rem; font-weight: 900;
            line-height: 1.1;
            margin-bottom: 16px;
            text-shadow: 0 4px 30px rgba(0,0,0,0.5);
        }
        .hero-meta {
            display: flex; align-items: center; gap: 20px;
            margin-bottom: 20px;
            color: var(--text-secondary);
            font-size: 0.95rem;
        }
        .hero-meta .rating {
            display: flex; align-items: center; gap: 5px;
            color: #ffd700;
        }
        .hero-overview {
            font-size: 1.05rem;
            line-height: 1.7;
            color: var(--text-secondary);
            margin-bottom: 30px;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        .hero-buttons {
            display: flex; gap: 15px;
            flex-wrap: wrap;
        }
        .btn {
            display: inline-flex; align-items: center; gap: 10px;
            padding: 14px 32px;
            border-radius: var(--radius-sm);
            font-size: 1rem; font-weight: 600;
            cursor: pointer;
            transition: var(--transition);
            border: none; outline: none;
            text-decoration: none;
        }
        .btn-primary {
            background: var(--primary);
            color: white;
        }
        .btn-primary:hover {
            background: var(--primary-dark);
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(229, 9, 20, 0.4);
        }
        .btn-secondary {
            background: rgba(255,255,255,0.1);
            color: var(--text-primary);
            border: 1px solid rgba(255,255,255,0.2);
        }
        .btn-secondary:hover {
            background: rgba(255,255,255,0.2);
            transform: translateY(-2px);
        }
        .hero-dots {
            position: absolute; bottom: 30px; left: 50%;
            transform: translateX(-50%);
            display: flex; gap: 10px; z-index: 3;
        }
        .hero-dot {
            width: 10px; height: 10px;
            border-radius: 50%;
            background: rgba(255,255,255,0.3);
            cursor: pointer;
            transition: var(--transition);
        }
        .hero-dot.active {
            background: var(--primary);
            width: 30px; border-radius: 5px;
        }

        .section {
            padding: 60px 40px;
            max-width: 1600px;
            margin: 0 auto;
        }
        .section-header {
            display: flex; align-items: center;
            justify-content: space-between;
            margin-bottom: 30px;
        }
        .section-title {
            font-size: 1.8rem; font-weight: 700;
            display: flex; align-items: center; gap: 12px;
        }
        .section-title i { color: var(--primary); font-size: 1.3rem; }
        .view-all {
            color: var(--primary);
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
            display: flex; align-items: center; gap: 5px;
            transition: var(--transition);
        }
        .view-all:hover { gap: 10px; }

        .category-pills {
            display: flex; gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 40px;
            padding: 0 40px;
            max-width: 1600px;
            margin: 0 auto 40px;
        }
        .category-pill {
            padding: 10px 24px;
            border-radius: 25px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            font-size: 0.9rem; font-weight: 500;
            cursor: pointer;
            transition: var(--transition);
            display: flex; align-items: center; gap: 8px;
        }
        .category-pill:hover, .category-pill.active {
            background: var(--primary);
            color: white;
            border-color: var(--primary);
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(229, 9, 20, 0.3);
        }
        .category-pill i { font-size: 0.85rem; }

        .movie-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 25px;
        }
        .movie-card {
            position: relative;
            border-radius: var(--radius-md);
            overflow: hidden;
            background: var(--bg-card);
            cursor: pointer;
            transition: var(--transition);
            border: 1px solid var(--border);
        }
        .movie-card:hover {
            transform: translateY(-8px) scale(1.02);
            box-shadow: var(--shadow-lg);
            border-color: rgba(229, 9, 20, 0.3);
        }
        .movie-poster {
            position: relative;
            aspect-ratio: 2/3;
            overflow: hidden;
        }
        .movie-poster img {
            width: 100%; height: 100%;
            object-fit: cover;
            transition: var(--transition);
        }
        .movie-card:hover .movie-poster img { transform: scale(1.1); }
        .movie-overlay {
            position: absolute; inset: 0;
            background: linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.3) 50%, transparent 100%);
            opacity: 0;
            transition: var(--transition);
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            padding: 20px;
        }
        .movie-card:hover .movie-overlay { opacity: 1; }
        .play-btn {
            position: absolute; top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            width: 60px; height: 60px;
            border-radius: 50%;
            background: rgba(229, 9, 20, 0.9);
            color: white;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.5rem;
            opacity: 0;
            transition: var(--transition);
            border: 2px solid rgba(255,255,255,0.3);
            backdrop-filter: blur(10px);
        }
        .movie-card:hover .play-btn {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1);
        }
        .play-btn:hover {
            background: var(--primary);
            transform: translate(-50%, -50%) scale(1.1);
        }
        .movie-rating {
            position: absolute; top: 10px; right: 10px;
            background: rgba(0,0,0,0.7);
            backdrop-filter: blur(10px);
            padding: 5px 10px;
            border-radius: var(--radius-sm);
            font-size: 0.8rem; font-weight: 700;
            color: #ffd700;
            display: flex; align-items: center; gap: 4px;
            border: 1px solid rgba(255,215,0,0.3);
        }
        .movie-badge {
            position: absolute; top: 10px; left: 10px;
            background: var(--primary);
            color: white;
            padding: 4px 10px;
            border-radius: var(--radius-sm);
            font-size: 0.7rem; font-weight: 700;
            text-transform: uppercase;
        }
        .movie-info { padding: 15px; }
        .movie-title {
            font-size: 0.95rem; font-weight: 600;
            margin-bottom: 6px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .movie-meta {
            display: flex; align-items: center;
            justify-content: space-between;
            color: var(--text-muted);
            font-size: 0.8rem;
        }
        .movie-genre {
            color: var(--primary);
            font-weight: 500;
        }

        .modal-overlay {
            position: fixed; inset: 0;
            background: rgba(0,0,0,0.95);
            backdrop-filter: blur(20px);
            z-index: 2000;
            display: none;
            align-items: center; justify-content: center;
            padding: 20px;
            opacity: 0;
            transition: opacity 0.3s;
        }
        .modal-overlay.active {
            display: flex;
            opacity: 1;
        }
        .modal-content {
            width: 100%; max-width: 1200px;
            background: var(--bg-card);
            border-radius: var(--radius-lg);
            overflow: hidden;
            border: 1px solid var(--border);
            box-shadow: var(--shadow-lg);
            transform: scale(0.9);
            transition: transform 0.3s;
        }
        .modal-overlay.active .modal-content { transform: scale(1); }
        .modal-header {
            display: flex; align-items: center;
            justify-content: space-between;
            padding: 20px 30px;
            border-bottom: 1px solid var(--border);
        }
        .modal-title {
            font-size: 1.3rem; font-weight: 700;
            display: flex; align-items: center; gap: 10px;
        }
        .modal-close {
            width: 40px; height: 40px;
            border-radius: 50%;
            background: rgba(255,255,255,0.1);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            display: flex; align-items: center; justify-content: center;
            cursor: pointer;
            transition: var(--transition);
            font-size: 1.2rem;
        }
        .modal-close:hover {
            background: var(--primary);
            color: white; border-color: var(--primary);
        }
        .video-container {
            position: relative;
            width: 100%;
            aspect-ratio: 16/9;
            background: #000;
        }
        .video-container iframe {
            width: 100%; height: 100%;
            border: none;
        }
        .season-selector {
            padding: 20px 30px;
            border-bottom: 1px solid var(--border);
            display: none;
        }
        .season-selector.active { display: block; }
        .selector-label {
            font-size: 0.9rem; font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 12px;
            display: block;
        }
        .season-tabs {
            display: flex; gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 15px;
        }
        .season-tab {
            padding: 8px 20px;
            border-radius: var(--radius-sm);
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            cursor: pointer;
            transition: var(--transition);
            font-size: 0.9rem;
        }
        .season-tab:hover, .season-tab.active {
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }
        .episode-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 10px;
        }
        .episode-btn {
            padding: 10px;
            border-radius: var(--radius-sm);
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            cursor: pointer;
            transition: var(--transition);
            text-align: center;
            font-size: 0.85rem;
        }
        .episode-btn:hover, .episode-btn.active {
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }
        .modal-details {
            padding: 25px 30px;
            display: grid;
            grid-template-columns: 150px 1fr;
            gap: 25px;
        }
        .modal-poster {
            width: 150px;
            border-radius: var(--radius-md);
            overflow: hidden;
            border: 1px solid var(--border);
        }
        .modal-poster img { width: 100%; display: block; }
        .modal-info h2 {
            font-size: 1.5rem; margin-bottom: 10px;
        }
        .modal-meta {
            display: flex; gap: 20px;
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        .modal-meta span {
            display: flex; align-items: center; gap: 5px;
        }
        .modal-overview {
            color: var(--text-secondary);
            line-height: 1.7;
            font-size: 0.95rem;
        }

        .search-results {
            display: none;
            padding: 100px 40px 60px;
            max-width: 1600px;
            margin: 0 auto;
        }
        .search-results.active { display: block; }
        .search-header { margin-bottom: 30px; }
        .search-header h2 {
            font-size: 1.5rem;
            display: flex; align-items: center; gap: 10px;
        }
        .search-header h2 span { color: var(--primary); }
        .no-results {
            text-align: center;
            padding: 80px 20px;
            color: var(--text-muted);
        }
        .no-results i {
            font-size: 4rem;
            margin-bottom: 20px;
            opacity: 0.5;
        }
        .no-results h3 {
            font-size: 1.5rem;
            margin-bottom: 10px;
            color: var(--text-secondary);
        }

        .footer {
            background: rgba(0,0,0,0.5);
            border-top: 1px solid var(--border);
            padding: 50px 40px 30px;
            margin-top: 60px;
        }
        .footer-content {
            max-width: 1600px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 2fr 1fr 1fr 1fr;
            gap: 40px;
        }
        .footer-brand .logo {
            margin-bottom: 15px;
            font-size: 1.5rem;
        }
        .footer-brand p {
            color: var(--text-muted);
            font-size: 0.9rem;
            line-height: 1.7;
        }
        .footer-column h4 {
            font-size: 1rem; margin-bottom: 20px;
            color: var(--text-primary);
        }
        .footer-column ul { list-style: none; }
        .footer-column ul li { margin-bottom: 12px; }
        .footer-column ul li a {
            color: var(--text-muted);
            text-decoration: none;
            font-size: 0.9rem;
            transition: var(--transition);
        }
        .footer-column ul li a:hover { color: var(--primary); }
        .footer-bottom {
            max-width: 1600px;
            margin: 40px auto 0;
            padding-top: 30px;
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: var(--text-muted);
            font-size: 0.85rem;
        }
        .footer-social { display: flex; gap: 15px; }
        .footer-social a {
            width: 40px; height: 40px;
            border-radius: 50%;
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            display: flex; align-items: center; justify-content: center;
            transition: var(--transition);
        }
        .footer-social a:hover {
            background: var(--primary);
            color: white; border-color: var(--primary);
        }

        @media (max-width: 1024px) {
            .hero { padding: 0 30px 60px; height: 70vh; }
            .hero-title { font-size: 2.5rem; }
            .footer-content { grid-template-columns: 1fr 1fr; }
        }
        @media (max-width: 768px) {
            .navbar { padding: 0 20px; }
            .nav-links { display: none; }
            .mobile-menu-btn { display: block; }
            .search-box input { width: 180px; }
            .search-box input:focus { width: 200px; }
            .hero { padding: 0 20px 40px; height: 60vh; min-height: 500px; }
            .hero-title { font-size: 2rem; }
            .hero-overview { font-size: 0.9rem; }
            .section { padding: 40px 20px; }
            .movie-grid { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; }
            .category-pills { padding: 0 20px; }
            .modal-details { grid-template-columns: 1fr; }
            .modal-poster { width: 120px; }
            .footer-content { grid-template-columns: 1fr; gap: 30px; }
            .footer-bottom { flex-direction: column; gap: 20px; text-align: center; }
        }

        .spinner {
            width: 40px; height: 40px;
            border: 3px solid rgba(255,255,255,0.1);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 40px auto;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        .toast {
            position: fixed; bottom: 30px; right: 30px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 16px 24px;
            display: flex; align-items: center; gap: 12px;
            box-shadow: var(--shadow-lg);
            z-index: 3000;
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s;
        }
        .toast.show {
            transform: translateY(0);
            opacity: 1;
        }
        .toast-icon {
            width: 36px; height: 36px;
            border-radius: 50%;
            background: rgba(229, 9, 20, 0.2);
            color: var(--primary);
            display: flex; align-items: center; justify-content: center;
        }
        .toast-text { font-size: 0.9rem; }

        .adblock-notice {
            position: fixed; bottom: 20px; left: 20px;
            background: linear-gradient(135deg, #1a1a2e, #0f3460);
            border: 1px solid rgba(229, 9, 20, 0.3);
            border-radius: var(--radius-md);
            padding: 16px 20px;
            max-width: 320px;
            z-index: 1500;
            box-shadow: var(--shadow-lg);
            display: none;
        }
        .adblock-notice.show { display: block; animation: slideIn 0.3s; }
        @keyframes slideIn {
            from { transform: translateX(-100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        .adblock-notice h4 {
            display: flex; align-items: center; gap: 8px;
            margin-bottom: 8px;
            color: var(--primary);
        }
        .adblock-notice p {
            font-size: 0.85rem;
            color: var(--text-secondary);
            line-height: 1.5;
        }
        .adblock-close {
            position: absolute; top: 10px; right: 10px;
            background: none; border: none;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 0.9rem;
        }

        .page-section { display: none; }
        .page-section.active { display: block; }
    </style>
</head>
<body>

<div class="loading-screen" id="loadingScreen">
    <div class="loading-logo"><i class="fas fa-film"></i> NILO CINEMA</div>
    <div class="loading-bar"><div class="loading-bar-fill"></div></div>
</div>

<nav class="navbar" id="navbar">
    <div class="nav-left">
        <div class="logo" onclick="showPage('home')">
            <i class="fas fa-film"></i> NILO CINEMA
        </div>
        <ul class="nav-links">
            <li><a href="#" class="active" onclick="showPage('home')">Home</a></li>
            <li><a href="#" onclick="showPage('movies')">Movies</a></li>
            <li><a href="#" onclick="showPage('tv')">TV Series</a></li>
            <li><a href="#" onclick="showPage('categories')">Categories</a></li>
        </ul>
    </div>
    <div class="nav-right">
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="Search movies, series..." onkeyup="handleSearch(event)">
            <button onclick="performSearch()"><i class="fas fa-search"></i></button>
        </div>
        <div class="nav-icon" onclick="showPage('home')" title="Home"><i class="fas fa-home"></i></div>
        <button class="mobile-menu-btn" onclick="toggleMobileMenu()"><i class="fas fa-bars"></i></button>
    </div>
</nav>

<!-- HOME PAGE -->
<div class="page-section active" id="homePage">
    <div class="hero" id="heroSection">
        <div class="hero-bg" id="heroBg" style="background-image: url('https://image.tmdb.org/t/p/original/8ZTVqvKDQ8emSGUEMjsS4yHAwrp.jpg')"></div>
        <div class="hero-content">
            <div class="hero-badge"><i class="fas fa-fire"></i> Trending Now</div>
            <h1 class="hero-title" id="heroTitle">Loading...</h1>
            <div class="hero-meta" id="heroMeta">
                <span class="rating"><i class="fas fa-star"></i> <span id="heroRating">--</span></span>
                <span id="heroYear">--</span>
                <span id="heroGenre">--</span>
            </div>
            <p class="hero-overview" id="heroOverview">Loading featured content...</p>
            <div class="hero-buttons">
                <button class="btn btn-primary" id="heroPlayBtn" onclick="playHero()">
                    <i class="fas fa-play"></i> Watch Now
                </button>
                <button class="btn btn-secondary" onclick="showHeroDetails()">
                    <i class="fas fa-info-circle"></i> More Info
                </button>
            </div>
        </div>
        <div class="hero-dots" id="heroDots"></div>
    </div>

    <div class="category-pills" id="categoryPills">
        <div class="category-pill active" onclick="filterByCategory('all')">
            <i class="fas fa-th-large"></i> All
        </div>
        <div class="category-pill" onclick="filterByCategory(27)">
            <i class="fas fa-ghost"></i> Horror
        </div>
        <div class="category-pill" onclick="filterByCategory(28)">
            <i class="fas fa-fist-raised"></i> Action
        </div>
        <div class="category-pill" onclick="filterByCategory(16)">
            <i class="fas fa-child"></i> Kids
        </div>
        <div class="category-pill" onclick="filterByCategory(16)">
            <i class="fas fa-magic"></i> Animation
        </div>
        <div class="category-pill" onclick="filterByCategory(10749)">
            <i class="fas fa-heart"></i> Romance
        </div>
        <div class="category-pill" onclick="filterByCategory(35)">
            <i class="fas fa-laugh-beam"></i> Comedy
        </div>
    </div>

    <div class="section">
        <div class="section-header">
            <h2 class="section-title"><i class="fas fa-fire"></i> Trending Movies</h2>
            <a href="#" class="view-all" onclick="showPage('movies')">View All <i class="fas fa-arrow-right"></i></a>
        </div>
        <div class="movie-grid" id="trendingMovies"></div>
    </div>

    <div class="section">
        <div class="section-header">
            <h2 class="section-title"><i class="fas fa-chart-line"></i> Popular Movies</h2>
            <a href="#" class="view-all" onclick="showPage('movies')">View All <i class="fas fa-arrow-right"></i></a>
        </div>
        <div class="movie-grid" id="popularMovies"></div>
    </div>

    <div class="section">
        <div class="section-header">
            <h2 class="section-title"><i class="fas fa-tv"></i> Trending TV Series</h2>
            <a href="#" class="view-all" onclick="showPage('tv')">View All <i class="fas fa-arrow-right"></i></a>
        </div>
        <div class="movie-grid" id="trendingTV"></div>
    </div>

    <div class="section">
        <div class="section-header">
            <h2 class="section-title"><i class="fas fa-star"></i> Popular TV Series</h2>
            <a href="#" class="view-all" onclick="showPage('tv')">View All <i class="fas fa-arrow-right"></i></a>
        </div>
        <div class="movie-grid" id="popularTV"></div>
    </div>

    <div class="section">
        <div class="section-header">
            <h2 class="section-title"><i class="fas fa-trophy"></i> Top Rated</h2>
            <a href="#" class="view-all" onclick="showPage('movies')">View All <i class="fas fa-arrow-right"></i></a>
        </div>
        <div class="movie-grid" id="topRated"></div>
    </div>
</div>

<!-- MOVIES PAGE -->
<div class="page-section" id="moviesPage">
    <div style="padding-top: 100px;">
        <div class="section">
            <div class="section-header">
                <h2 class="section-title"><i class="fas fa-film"></i> All Movies</h2>
            </div>
            <div class="movie-grid" id="allMovies"></div>
            <div class="spinner" id="moviesSpinner" style="display:none;"></div>
        </div>
    </div>
</div>

<!-- TV SERIES PAGE -->
<div class="page-section" id="tvPage">
    <div style="padding-top: 100px;">
        <div class="section">
            <div class="section-header">
                <h2 class="section-title"><i class="fas fa-tv"></i> All TV Series</h2>
            </div>
            <div class="movie-grid" id="allTV"></div>
            <div class="spinner" id="tvSpinner" style="display:none;"></div>
        </div>
    </div>
</div>

<!-- CATEGORIES PAGE -->
<div class="page-section" id="categoriesPage">
    <div style="padding-top: 100px;">
        <div class="section">
            <div class="section-header">
                <h2 class="section-title"><i class="fas fa-th-large"></i> Browse by Category</h2>
            </div>
            <div class="category-pills" style="margin-bottom: 40px;">
                <div class="category-pill active" onclick="filterCategoryPage('all')">
                    <i class="fas fa-th-large"></i> All
                </div>
                <div class="category-pill" onclick="filterCategoryPage(27)">
                    <i class="fas fa-ghost"></i> Horror
                </div>
                <div class="category-pill" onclick="filterCategoryPage(28)">
                    <i class="fas fa-fist-raised"></i> Action
                </div>
                <div class="category-pill" onclick="filterCategoryPage(16)">
                    <i class="fas fa-child"></i> Kids
                </div>
                <div class="category-pill" onclick="filterCategoryPage(16)">
                    <i class="fas fa-magic"></i> Animation
                </div>
                <div class="category-pill" onclick="filterCategoryPage(10749)">
                    <i class="fas fa-heart"></i> Romance
                </div>
                <div class="category-pill" onclick="filterCategoryPage(35)">
                    <i class="fas fa-laugh-beam"></i> Comedy
                </div>
            </div>
            <div class="movie-grid" id="categoryResults"></div>
            <div class="spinner" id="categorySpinner" style="display:none;"></div>
        </div>
    </div>
</div>

<!-- SEARCH RESULTS -->
<div class="search-results" id="searchResults">
    <div class="search-header">
        <h2><i class="fas fa-search"></i> Search Results for "<span id="searchQuery"></span>"</h2>
    </div>
    <div class="movie-grid" id="searchGrid"></div>
    <div class="no-results" id="noResults" style="display:none;">
        <i class="fas fa-film"></i>
        <h3>No results found</h3>
        <p>Try searching with different keywords</p>
    </div>
</div>

<!-- Player Modal -->
<div class="modal-overlay" id="playerModal">
    <div class="modal-content">
        <div class="modal-header">
            <div class="modal-title" id="modalTitle"><i class="fas fa-play-circle"></i> Now Playing</div>
            <button class="modal-close" onclick="closeModal()"><i class="fas fa-times"></i></button>
        </div>
        <div class="video-container" id="videoContainer">
            <iframe id="videoFrame" allowfullscreen></iframe>
        </div>
        <div class="season-selector" id="seasonSelector">
            <span class="selector-label"><i class="fas fa-list"></i> Select Season</span>
            <div class="season-tabs" id="seasonTabs"></div>
            <span class="selector-label"><i class="fas fa-play"></i> Select Episode</span>
            <div class="episode-grid" id="episodeGrid"></div>
        </div>
        <div class="modal-details">
            <div class="modal-poster" id="modalPoster">
                <img src="" alt="Poster" id="modalPosterImg">
            </div>
            <div class="modal-info">
                <h2 id="modalMovieTitle">Title</h2>
                <div class="modal-meta">
                    <span class="rating"><i class="fas fa-star" style="color:#ffd700"></i> <span id="modalRating">--</span></span>
                    <span><i class="fas fa-calendar"></i> <span id="modalYear">--</span></span>
                    <span><i class="fas fa-clock"></i> <span id="modalRuntime">--</span></span>
                    <span id="modalGenre"><i class="fas fa-tag"></i> --</span>
                </div>
                <p class="modal-overview" id="modalOverview">Overview</p>
            </div>
        </div>
    </div>
</div>

<div class="adblock-notice" id="adblockNotice">
    <button class="adblock-close" onclick="document.getElementById('adblockNotice').classList.remove('show')"><i class="fas fa-times"></i></button>
    <h4><i class="fas fa-shield-alt"></i> Ad Blocker Recommended</h4>
    <p>For the best viewing experience, we recommend using an ad blocker extension like uBlock Origin or AdBlock Plus.</p>
</div>

<div class="toast" id="toast">
    <div class="toast-icon"><i class="fas fa-info-circle"></i></div>
    <div class="toast-text" id="toastText">Notification</div>
</div>

<footer class="footer">
    <div class="footer-content">
        <div class="footer-brand">
            <div class="logo"><i class="fas fa-film"></i> NILO CINEMA</div>
            <p>Your ultimate destination for movies and TV series. Watch the latest releases, trending shows, and all-time classics in one place.</p>
        </div>
        <div class="footer-column">
            <h4>Navigation</h4>
            <ul>
                <li><a href="#" onclick="showPage('home')">Home</a></li>
                <li><a href="#" onclick="showPage('movies')">Movies</a></li>
                <li><a href="#" onclick="showPage('tv')">TV Series</a></li>
                <li><a href="#" onclick="showPage('categories')">Categories</a></li>
            </ul>
        </div>
        <div class="footer-column">
            <h4>Categories</h4>
            <ul>
                <li><a href="#" onclick="filterByCategory(27)">Horror</a></li>
                <li><a href="#" onclick="filterByCategory(28)">Action</a></li>
                <li><a href="#" onclick="filterByCategory(16)">Animation</a></li>
                <li><a href="#" onclick="filterByCategory(35)">Comedy</a></li>
            </ul>
        </div>
        <div class="footer-column">
            <h4>Legal</h4>
            <ul>
                <li><a href="#">Terms of Service</a></li>
                <li><a href="#">Privacy Policy</a></li>
                <li><a href="#">DMCA</a></li>
                <li><a href="#">Contact Us</a></li>
            </ul>
        </div>
    </div>
    <div class="footer-bottom">
        <div>&copy; 2026 Nilo Cinema. All rights reserved.</div>
        <div class="footer-social">
            <a href="#"><i class="fab fa-facebook-f"></i></a>
            <a href="#"><i class="fab fa-twitter"></i></a>
            <a href="#"><i class="fab fa-instagram"></i></a>
            <a href="#"><i class="fab fa-youtube"></i></a>
        </div>
    </div>
</footer>

<script>
const API_KEY = 'f519e4673f7652685cfc57630b824606';
const BASE_URL = 'https://api.themoviedb.org/3';
const IMG_URL = 'https://image.tmdb.org/t/p/w500';
const IMG_ORIGINAL = 'https://image.tmdb.org/t/p/original';
const VID_SRC_MOVIE = 'https://vidsrc.pm/embed/movie/';
const VID_SRC_TV = 'https://vidsrc.pm/embed/tv/';

const GENRES = {
    28: 'Action', 12: 'Adventure', 16: 'Animation', 35: 'Comedy',
    80: 'Crime', 99: 'Documentary', 18: 'Drama', 10751: 'Family',
    14: 'Fantasy', 36: 'History', 27: 'Horror', 10402: 'Music',
    9648: 'Mystery', 10749: 'Romance', 878: 'Science Fiction',
    10770: 'TV Movie', 53: 'Thriller', 10752: 'War', 37: 'Western'
};

let currentHeroIndex = 0;
let heroMovies = [];
let currentMovie = null;
let currentTVSeasons = [];
let currentSeason = 1;

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        document.getElementById('loadingScreen').classList.add('hidden');
    }, 2000);
    
    initApp();
    
    setTimeout(() => {
        document.getElementById('adblockNotice').classList.add('show');
    }, 3000);
    
    window.addEventListener('scroll', () => {
        const navbar = document.getElementById('navbar');
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });
});

async function initApp() {
    await loadHeroMovies();
    await loadTrendingMovies();
    await loadPopularMovies();
    await loadTrendingTV();
    await loadPopularTV();
    await loadTopRated();
    await loadAllMovies();
    await loadAllTV();
}

async function fetchTMDB(endpoint) {
    try {
        const response = await fetch(`${BASE_URL}${endpoint}&api_key=${API_KEY}`);
        if (!response.ok) throw new Error('API Error');
        return await response.json();
    } catch (error) {
        console.error('TMDB API Error:', error);
        showToast('Failed to load content. Please try again.');
        return null;
    }
}

async function loadHeroMovies() {
    const data = await fetchTMDB('/trending/movie/week?language=en-US');
    if (data && data.results) {
        heroMovies = data.results.slice(0, 5);
        updateHero();
        createHeroDots();
        setInterval(rotateHero, 6000);
    }
}

function updateHero() {
    const movie = heroMovies[currentHeroIndex];
    if (!movie) return;
    
    document.getElementById('heroBg').style.backgroundImage = `url('${IMG_ORIGINAL}${movie.backdrop_path || movie.poster_path}')`;
    document.getElementById('heroTitle').textContent = movie.title;
    document.getElementById('heroRating').textContent = movie.vote_average?.toFixed(1) || 'N/A';
    document.getElementById('heroYear').textContent = movie.release_date ? movie.release_date.split('-')[0] : 'N/A';
    document.getElementById('heroGenre').textContent = getGenreNames(movie.genre_ids);
    document.getElementById('heroOverview').textContent = movie.overview || 'No overview available.';
    
    updateHeroDots();
}

function createHeroDots() {
    const container = document.getElementById('heroDots');
    container.innerHTML = '';
    heroMovies.forEach((_, i) => {
        const dot = document.createElement('div');
        dot.className = `hero-dot ${i === 0 ? 'active' : ''}`;
        dot.onclick = () => { currentHeroIndex = i; updateHero(); };
        container.appendChild(dot);
    });
}

function updateHeroDots() {
    document.querySelectorAll('.hero-dot').forEach((dot, i) => {
        dot.classList.toggle('active', i === currentHeroIndex);
    });
}

function rotateHero() {
    currentHeroIndex = (currentHeroIndex + 1) % heroMovies.length;
    updateHero();
}

function playHero() {
    const movie = heroMovies[currentHeroIndex];
    if (movie) openPlayer(movie.id, 'movie', movie);
}

function showHeroDetails() {
    const movie = heroMovies[currentHeroIndex];
    if (movie) openPlayer(movie.id, 'movie', movie);
}

async function loadTrendingMovies() {
    const data = await fetchTMDB('/trending/movie/week?language=en-US');
    if (data) renderMovies(data.results, 'trendingMovies');
}

async function loadPopularMovies() {
    const data = await fetchTMDB('/movie/popular?language=en-US&page=1');
    if (data) renderMovies(data.results, 'popularMovies');
}

async function loadTrendingTV() {
    const data = await fetchTMDB('/trending/tv/week?language=en-US');
    if (data) renderMovies(data.results, 'trendingTV', 'tv');
}

async function loadPopularTV() {
    const data = await fetchTMDB('/tv/popular?language=en-US&page=1');
    if (data) renderMovies(data.results, 'popularTV', 'tv');
}

async function loadTopRated() {
    const data = await fetchTMDB('/movie/top_rated?language=en-US&page=1');
    if (data) renderMovies(data.results, 'topRated');
}

async function loadAllMovies() {
    const data = await fetchTMDB('/movie/popular?language=en-US&page=1');
    if (data) renderMovies(data.results, 'allMovies');
}

async function loadAllTV() {
    const data = await fetchTMDB('/tv/popular?language=en-US&page=1');
    if (data) renderMovies(data.results, 'allTV', 'tv');
}

function renderMovies(movies, containerId, type = 'movie') {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = movies.map(movie => createMovieCard(movie, type)).join('');
}

function createMovieCard(movie, type = 'movie') {
    const poster = movie.poster_path ? IMG_URL + movie.poster_path : 'https://via.placeholder.com/300x450/1a1a1a/666?text=No+Poster';
    const title = movie.title || movie.name || 'Unknown';
    const year = (movie.release_date || movie.first_air_date || '').split('-')[0] || 'N/A';
    const rating = movie.vote_average ? movie.vote_average.toFixed(1) : 'N/A';
    const genre = getGenreNames(movie.genre_ids);
    const badge = type === 'tv' ? '<span class="movie-badge">TV Series</span>' : '';
    
    return `
        <div class="movie-card" onclick='openPlayer(${movie.id}, "${type}", ${JSON.stringify(movie).replace(/"/g, '&quot;')})'>
            <div class="movie-poster">
                <img src="${poster}" alt="${title}" loading="lazy">
                <div class="movie-overlay">
                    <div class="play-btn"><i class="fas fa-play"></i></div>
                </div>
                ${badge}
                <div class="movie-rating"><i class="fas fa-star"></i> ${rating}</div>
            </div>
            <div class="movie-info">
                <div class="movie-title">${title}</div>
                <div class="movie-meta">
                    <span>${year}</span>
                    <span class="movie-genre">${genre}</span>
                </div>
            </div>
        </div>
    `;
}

function getGenreNames(genreIds) {
    if (!genreIds || !genreIds.length) return 'N/A';
    return genreIds.slice(0, 2).map(id => GENRES[id] || '').filter(Boolean).join(', ') || 'N/A';
}

async function openPlayer(id, type, movieData) {
    currentMovie = movieData;
    const modal = document.getElementById('playerModal');
    const name = movieData.title || movieData.name || 'Unknown';
    const poster = movieData.poster_path ? IMG_URL + movieData.poster_path : '';
    const year = (movieData.release_date || movieData.first_air_date || '').split('-')[0] || 'N/A';
    
    document.getElementById('modalTitle').innerHTML = `<i class="fas fa-play-circle"></i> ${name}`;
    document.getElementById('modalMovieTitle').textContent = name;
    document.getElementById('modalPosterImg').src = poster;
    document.getElementById('modalRating').textContent = movieData.vote_average?.toFixed(1) || 'N/A';
    document.getElementById('modalYear').textContent = year;
    document.getElementById('modalGenre').innerHTML = `<i class="fas fa-tag"></i> ${getGenreNames(movieData.genre_ids)}`;
    document.getElementById('modalOverview').textContent = movieData.overview || 'No overview available.';
    
    if (type === 'tv') {
        document.getElementById('seasonSelector').classList.add('active');
        await loadTVDetails(id);
    } else {
        document.getElementById('seasonSelector').classList.remove('active');
        document.getElementById('videoFrame').src = `${VID_SRC_MOVIE}${id}`;
        document.getElementById('modalRuntime').textContent = movieData.runtime ? `${movieData.runtime} min` : 'N/A';
    }
    
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

async function loadTVDetails(tvId) {
    const data = await fetchTMDB(`/tv/${tvId}?language=en-US`);
    if (!data) return;
    
    currentTVSeasons = data.seasons || [];
    currentSeason = 1;
    
    document.getElementById('modalRuntime').textContent = `${data.number_of_seasons} Seasons`;
    
    renderSeasonTabs();
    loadEpisodes(tvId, currentSeason);
    
    document.getElementById('videoFrame').src = `${VID_SRC_TV}${tvId}/${currentSeason}/1`;
}

function renderSeasonTabs() {
    const container = document.getElementById('seasonTabs');
    container.innerHTML = currentTVSeasons
        .filter(s => s.season_number > 0)
        .map(s => `
            <div class="season-tab ${s.season_number === currentSeason ? 'active' : ''}" 
                 onclick="selectSeason(${s.season_number})">
                Season ${s.season_number}
            </div>
        `).join('');
}

async function loadEpisodes(tvId, seasonNum) {
    const data = await fetchTMDB(`/tv/${tvId}/season/${seasonNum}?language=en-US`);
    if (!data) return;
    
    const container = document.getElementById('episodeGrid');
    const episodes = data.episodes || [];
    
    container.innerHTML = episodes.map((ep, i) => `
        <div class="episode-btn ${i === 0 ? 'active' : ''}" 
             onclick="playEpisode(${tvId}, ${seasonNum}, ${ep.episode_number}, this)">
            EP ${ep.episode_number}
        </div>
    `).join('');
}

function selectSeason(seasonNum) {
    currentSeason = seasonNum;
    renderSeasonTabs();
    loadEpisodes(currentMovie.id, seasonNum);
    document.getElementById('videoFrame').src = `${VID_SRC_TV}${currentMovie.id}/${seasonNum}/1`;
}

function playEpisode(tvId, season, episode, btn) {
    document.querySelectorAll('.episode-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('videoFrame').src = `${VID_SRC_TV}${tvId}/${season}/${episode}`;
}

function closeModal() {
    document.getElementById('playerModal').classList.remove('active');
    document.getElementById('videoFrame').src = '';
    document.body.style.overflow = '';
}

function handleSearch(e) {
    if (e.key === 'Enter') performSearch();
}

async function performSearch() {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) return;
    
    document.getElementById('searchQuery').textContent = query;
    document.getElementById('searchResults').classList.add('active');
    document.getElementById('noResults').style.display = 'none';
    document.getElementById('searchGrid').innerHTML = '<div class="spinner"></div>';
    
    document.querySelectorAll('.page-section').forEach(p => p.classList.remove('active'));
    
    const [movieData, tvData] = await Promise.all([
        fetchTMDB(`/search/movie?query=${encodeURIComponent(query)}&language=en-US&page=1`),
        fetchTMDB(`/search/tv?query=${encodeURIComponent(query)}&language=en-US&page=1`)
    ]);
    
    const allResults = [...(movieData?.results || []), ...(tvData?.results || [])];
    
    if (allResults.length === 0) {
        document.getElementById('searchGrid').innerHTML = '';
        document.getElementById('noResults').style.display = 'block';
    } else {
        renderMovies(allResults, 'searchGrid');
    }
    
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function filterByCategory(genreId) {
    document.querySelectorAll('#categoryPills .category-pill').forEach(pill => {
        pill.classList.remove('active');
    });
    event.target.closest('.category-pill').classList.add('active');
    
    if (genreId === 'all') {
        await loadTrendingMovies();
        await loadPopularMovies();
        return;
    }
    
    const data = await fetchTMDB(`/discover/movie?with_genres=${genreId}&language=en-US&sort_by=popularity.desc&page=1`);
    if (data) {
        renderMovies(data.results.slice(0, 12), 'trendingMovies');
        document.getElementById('popularMovies').innerHTML = '';
    }
}

async function filterCategoryPage(genreId) {
    document.querySelectorAll('#categoriesPage .category-pill').forEach(pill => {
        pill.classList.remove('active');
    });
    event.target.closest('.category-pill').classList.add('active');
    
    const container = document.getElementById('categoryResults');
    const spinner = document.getElementById('categorySpinner');
    
    container.innerHTML = '';
    spinner.style.display = 'block';
    
    if (genreId === 'all') {
        const [movieData, tvData] = await Promise.all([
            fetchTMDB('/movie/popular?language=en-US&page=1'),
            fetchTMDB('/tv/popular?language=en-US&page=1')
        ]);
        const allResults = [...(movieData?.results || []), ...(tvData?.results || [])];
        renderMovies(allResults, 'categoryResults');
    } else {
        const [movieData, tvData] = await Promise.all([
            fetchTMDB(`/discover/movie?with_genres=${genreId}&language=en-US&sort_by=popularity.desc&page=1`),
            fetchTMDB(`/discover/tv?with_genres=${genreId}&language=en-US&sort_by=popularity.desc&page=1`)
        ]);
        const allResults = [...(movieData?.results || []), ...(tvData?.results || [])];
        renderMovies(allResults, 'categoryResults');
    }
    
    spinner.style.display = 'none';
}

function showPage(page) {
    document.getElementById('searchResults').classList.remove('active');
    document.getElementById('searchInput').value = '';
    
    document.querySelectorAll('.page-section').forEach(p => p.classList.remove('active'));
    document.getElementById(page + 'Page').classList.add('active');
    
    document.querySelectorAll('.nav-links a').forEach(link => {
        link.classList.remove('active');
        if (link.textContent.toLowerCase().includes(page === 'home' ? 'home' : page)) {
            link.classList.add('active');
        }
    });
    
    window.scrollTo({ top: 0, behavior: 'smooth' });
    
    if (page === 'categories') {
        filterCategoryPage('all');
    }
}

function toggleMobileMenu() {
    const navLinks = document.querySelector('.nav-links');
    if (navLinks.style.display === 'flex') {
        navLinks.style.display = 'none';
    } else {
        navLinks.style.display = 'flex';
        navLinks.style.position = 'absolute';
        navLinks.style.top = '70px';
        navLinks.style.left = '0';
        navLinks.style.right = '0';
        navLinks.style.flexDirection = 'column';
        navLinks.style.background = 'rgba(15,15,15,0.98)';
        navLinks.style.padding = '20px';
        navLinks.style.gap = '15px';
        navLinks.style.borderBottom = '1px solid var(--border)';
    }
}

function showToast(message) {
    const toast = document.getElementById('toast');
    document.getElementById('toastText').textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

// Close modal on escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});
</script>
</body>
</html>'''

with open('/mnt/agents/output/nilo_cinema.html', 'w', encoding='utf-8') as f:
    f.write(html_code)

print("File saved successfully!")
print(f"Total characters: {len(html_code)}")