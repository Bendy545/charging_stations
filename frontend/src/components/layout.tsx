// layout.tsx
import React from 'react';
import { Link, useLocation } from 'react-router-dom';

interface LayoutProps {
    children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
    const location = useLocation();

    // Pomocná funkce pro aktivní linky s moderním stylem
    const getLinkClass = (path: string) => {
        const isActive = location.pathname === path;
        return `btn d-flex align-items-center gap-2 px-3 py-2 rounded-3 transition-all ${
            isActive
                ? 'bg-white text-primary shadow-sm fw-medium'
                : 'text-white-50 hover-text-white'
        }`;
    };

    return (
        <div style={{ minHeight: '100vh', backgroundColor: '#f3f4f6', fontFamily: "'Inter', sans-serif" }}>
            <nav className="navbar navbar-dark shadow-sm"
                 style={{ background: 'linear-gradient(90deg, #fd7e14 0%, #e65100 100%)' }}>
                <div className="container-fluid px-4">
                    <Link to="/" className="navbar-brand d-flex align-items-center gap-2 fw-bold">
                        <span>EnergyMonitor</span>
                    </Link>

                    <div className="d-flex align-items-center gap-3">
                        <Link to="/" className={getLinkClass('/')} style={{ border: 'none' }}>
                            <i className="bi bi-grid-fill"></i>
                            Dashboard
                        </Link>
                        <Link to="/predictions" className={getLinkClass('/predictions')} style={{ border: 'none' }}>
                            <i className="bi bi-stars"></i>
                            Predictions
                        </Link>
                    </div>
                </div>
            </nav>

            <main className="py-4 fade-in">
                {children}
            </main>

            <footer className="mt-auto py-4 text-center text-muted border-top bg-white">
                <small>© 2026 Charging Station Analytics • Powered by ML</small>
            </footer>

            {/* Přidej toto do svého CSS souboru pro hladké přechody */}
            <style>{`
                .transition-all { transition: all 0.2s ease-in-out; }
                .hover-text-white:hover { color: white !important; background: rgba(255,255,255,0.1); }
            `}</style>
        </div>
    );
};

export default Layout;