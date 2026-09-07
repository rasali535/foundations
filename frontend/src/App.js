import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import "@/App.css";

// Public Components & Pages
import Layout from "@/components/Layout";
import Home from "@/pages/Home";
import About from "@/pages/About";
import Services from "@/pages/Services";
import ServiceDetail from "@/pages/ServiceDetail";
import Counselling from "@/pages/Counselling";
import CorporateWellness from "@/pages/CorporateWellness";
import TrainingTeamBuilding from "@/pages/TrainingTeamBuilding";
import Learning from "@/pages/Learning";
import CoursePreview from "@/pages/CoursePreview";
import Resources from "@/pages/Resources";
import Approach from "@/pages/Approach";
import Industries from "@/pages/Industries";
import Impact from "@/pages/Impact";
import Team from "@/pages/Team";
import Contact from "@/pages/Contact";
import Privacy from "@/pages/Privacy";
import Terms from "@/pages/Terms";
import Cookies from "@/pages/Cookies";
import Disclaimer from "@/pages/Disclaimer";
import Refunds from "@/pages/Refunds";
import NotFound from "@/pages/NotFound";
import IntakeForm from "@/pages/IntakeForm";

// Admin CRM & Booking Platform Components
import { AdminAuthProvider } from "@/admin/AdminAuthContext";
import AdminLayout from "@/admin/AdminLayout";
import AdminLogin from "@/admin/pages/AdminLogin";
import AdminDashboard from "@/admin/pages/AdminDashboard";
import AdminClients from "@/admin/pages/AdminClients";
import AdminClientDetail from "@/admin/pages/AdminClientDetail";
import AdminBookings from "@/admin/pages/AdminBookings";
import AdminCalendar from "@/admin/pages/AdminCalendar";
import AdminTherapists from "@/admin/pages/AdminTherapists";
import AdminSettings from "@/admin/pages/AdminSettings";

function App() {
  return (
    <div className="App">
      <AdminAuthProvider>
        <BrowserRouter>
          <Routes>
            {/* ================= Protected Admin CRM & Booking Routes ================= */}
            <Route path="/admin/login" element={<AdminLogin />} />
            
            <Route path="/admin" element={<AdminLayout />}>
              <Route index element={<Navigate to="/admin/dashboard" replace />} />
              <Route path="dashboard" element={<AdminDashboard />} />
              <Route path="crm" element={<Navigate to="/admin/crm/clients" replace />} />
              <Route path="crm/clients" element={<AdminClients />} />
              <Route path="crm/clients/:id" element={<AdminClientDetail />} />
              <Route path="bookings" element={<AdminBookings />} />
              <Route path="calendar" element={<AdminCalendar />} />
              <Route path="therapists" element={<AdminTherapists />} />
              <Route path="settings" element={<AdminSettings />} />
            </Route>

            {/* ================= Public FCA Website (UNTOUCHED VISUALS/UX) ================= */}
            <Route element={<Layout />}>
              {/* Primary 4 Core Pathways */}
              <Route path="/" element={<Home />} />
              <Route path="/counselling" element={<Counselling />} />
              <Route path="/corporate-wellness" element={<CorporateWellness />} />
              <Route path="/training-team-building" element={<TrainingTeamBuilding />} />
              <Route path="/learning" element={<Learning />} />
              <Route path="/learning/:slug" element={<CoursePreview />} />

              {/* Supporting & Legal Pages */}
              <Route path="/resources" element={<Resources />} />
              <Route path="/about" element={<About />} />
              <Route path="/contact" element={<Contact />} />
              <Route path="/privacy" element={<Privacy />} />
              <Route path="/terms" element={<Terms />} />
              <Route path="/cookies" element={<Cookies />} />
              <Route path="/disclaimer" element={<Disclaimer />} />
              <Route path="/refunds" element={<Refunds />} />
              <Route path="/intake" element={<IntakeForm />} />

              {/* Backwards Compatibility Routes */}
              <Route path="/services" element={<Services />} />
              <Route path="/services/:slug" element={<ServiceDetail />} />
              <Route path="/approach" element={<Approach />} />
              <Route path="/industries" element={<Industries />} />
              <Route path="/impact" element={<Impact />} />
              <Route path="/team" element={<Team />} />

              {/* 404 Catch-All */}
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AdminAuthProvider>
      <Toaster position="top-center" richColors />
    </div>
  );
}

export default App;
