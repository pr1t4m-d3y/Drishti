import { BrowserRouter, Routes, Route } from 'react-router-dom';
import SegmentSelect from './pages/SegmentSelect';
import Dashboard from './pages/Dashboard';
import CustomerDetail from './pages/CustomerDetail';
import Copilot from './pages/Copilot';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SegmentSelect />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/customer/:id" element={<CustomerDetail />} />
        <Route path="/copilot" element={<Copilot />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
