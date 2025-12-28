import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

import App from './App';
import Home from './home';
import Use from './pages/use';
import Baken from './pages/baken';
import RacePage from './pages/RacePage';
import Horse from './pages/horse';
import Jockey from './pages/jockey';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<App />}>
        <Route index element={<Home />} />
        <Route path="use" element={<Use />} />
        <Route path="baken" element={<Baken />} />
        <Route path="race/:venue/:raceNum" element={<RacePage />} />
        <Route path="horse/:horseName" element={<Horse />} />
        <Route path="jockey/:jockeyName" element={<Jockey />} />
      </Route>
    </Routes>
  </BrowserRouter>
);
