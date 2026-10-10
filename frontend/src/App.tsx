import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import DashboardView from './views/DashboardView';
import InventoryView from './views/InventoryView';
import SalesPurchasesView from './views/SalesPurchasesView';
import BuffetPlanningView from './views/BuffetPlanningView';
import SurplusWasteView from './views/SurplusWasteView';
import DonationCentresView from './views/DonationCentresView';
import DocumentsView from './views/DocumentsView';
import ImpactReportsView from './views/ImpactReportsView';
import SettingsView from './views/SettingsView';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<DashboardView />} />
          <Route path="/inventory" element={<InventoryView />} />
          <Route path="/sales-purchases" element={<SalesPurchasesView />} />
          <Route path="/buffet-planning" element={<BuffetPlanningView />} />
          <Route path="/surplus-waste" element={<SurplusWasteView />} />
          <Route path="/donations" element={<DonationCentresView />} />
          <Route path="/documents" element={<DocumentsView />} />
          <Route path="/impact" element={<ImpactReportsView />} />
          <Route path="/settings" element={<SettingsView />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
