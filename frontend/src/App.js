import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import "@/App.css";

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

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
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
      <Toaster position="top-center" richColors />
    </div>
  );
}

export default App;
