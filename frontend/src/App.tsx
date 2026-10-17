import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import DashboardView from './views/DashboardView';
import InventoryView from './views/InventoryView';
import PurchaseRecommendationsView from './views/PurchaseRecommendationsView';
import PurchaseInvoicesView from './views/PurchaseInvoicesView';
import BuffetPlanningView from './views/BuffetPlanningView';
import SurplusWasteView from './views/SurplusWasteView';
import DonationCentresView from './views/DonationCentresView';
import DocumentsView from './views/DocumentsView';
import ImpactReportsView from './views/ImpactReportsView';
import SettingsView from './views/SettingsView';
import RecipesView from './views/RecipesView';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<DashboardView />} />
          <Route path="/inventory" element={<InventoryView />} />
          <Route path="/sales-purchases" element={<PurchaseRecommendationsView />} />
          <Route path="/purchases" element={<PurchaseInvoicesView />} />
          <Route path="/recipes" element={<RecipesView />} />
          <Route path="/buffet-planning" element={<BuffetPlanningView />} />
          <Route path="/staff-consumption" element={<SurplusWasteView mode="staff" />} />
          <Route path="/waste" element={<SurplusWasteView mode="waste" />} />
          <Route path="/surplus-waste" element={<Navigate to="/waste" replace />} />
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
