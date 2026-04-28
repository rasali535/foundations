import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import "@/App.css";

import Layout from "@/components/Layout";
import Home from "@/pages/Home";
import About from "@/pages/About";
import Services from "@/pages/Services";
import ServiceDetail from "@/pages/ServiceDetail";
import CoursePreview from "@/pages/CoursePreview";
import Approach from "@/pages/Approach";
import Industries from "@/pages/Industries";
import Impact from "@/pages/Impact";
import Team from "@/pages/Team";
import Contact from "@/pages/Contact";
import Privacy from "@/pages/Privacy";
import NotFound from "@/pages/NotFound";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route path="/about" element={<About />} />
            <Route path="/services" element={<Services />} />
            <Route path="/services/:slug" element={<ServiceDetail />} />
            <Route path="/learning/:slug" element={<CoursePreview />} />
            <Route path="/approach" element={<Approach />} />
            <Route path="/industries" element={<Industries />} />
            <Route path="/impact" element={<Impact />} />
            <Route path="/team" element={<Team />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="top-center" richColors />
    </div>
  );
}

export default App;
