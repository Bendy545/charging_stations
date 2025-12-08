import React, { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Layout.css';

interface LayoutProps {
    children: ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
    const location = useLocation();

    return (
        <div className="layout">
            <header className="header">
                <div className="header-content">
                    <Link to="/" className="logo">
                        ⚡ Charging Station Analysis
                    </Link>
                    <nav className="nav">
                        <Link
                            to="/"
                            className={location.pathname === '/' ? 'nav-link active' : 'nav-link'}
                        >
                            Dashboard
                        </Link>
                    </nav>
                </div>
            </header>
            <main className="main-content">
                {children}
            </main>
            <footer className="footer">
                <p>&copy; 2025 Charging Station Loss Analysis</p>
            </footer>
        </div>
    );
};

export default Layout;