import React from 'react';
import { Link, useLocation } from 'react-router-dom';

interface LayoutProps {
    children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
    const location = useLocation();

    return (
        <div style={{ minHeight: '100vh', backgroundColor: '#f8f9fa' }}>
            <nav className="navbar navbar-dark bg-primary shadow-sm">
                <div className="container-fluid px-4">
                    <Link to="/" className="navbar-brand mb-0 h1 text-decoration-none">
                        <i className="bi bi-lightning-charge-fill me-2"></i>
                        Charging Station Loss Analysis System
                    </Link>
                    <div className="d-flex align-items-center">
                        <Link
                            to="/"
                            className={`btn ${
                                location.pathname === '/' ? 'btn-light' : 'btn-outline-light'
                            } me-2`}
                        >
                            <i className="bi bi-house-door me-1"></i>
                            Dashboard
                        </Link>
                    </div>
                </div>
            </nav>

            <main>{children}</main>

            <footer className="bg-white border-top mt-5 py-3">
                <div className="container-fluid px-4">
                    <div className="text-center text-muted small">
                        <p className="mb-0">
                            © 2024 Charging Station Loss Analysis System | Built with React + Vite
                        </p>
                    </div>
                </div>
            </footer>
        </div>
    );
};

export default Layout;