import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/layout';
import Dashboard from './pages/dashboard';
import StationDetail from './pages/stationDetail';
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