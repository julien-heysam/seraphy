import { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Box } from '@chakra-ui/react'

// Import pages
import HomePage from './pages/HomePage'
import DocumentPage from './pages/DocumentPage'
import DashboardPage from './pages/DashboardPage'
import NotFoundPage from './pages/NotFoundPage'

// Import components
import Navbar from './components/Navbar'
import Footer from './components/Footer'

function App() {
  return (
    <Box minH="100vh" display="flex" flexDirection="column">
      <Navbar />
      <Box flex="1" as="main">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/documents/:id" element={<DocumentPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Box>
      <Footer />
    </Box>
  )
}

export default App
