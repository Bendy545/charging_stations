import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import StationDetail from './pages/StationDetail';
import './App.css';

function App() {
    return (
        <Router>
            <Layout>
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/station/:stationId" element={<StationDetail />} />
                </Routes>
            </Layout>
        </Router>
    );
}

export default App;