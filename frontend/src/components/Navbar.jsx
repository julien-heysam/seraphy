import { Box, Flex, Button, Heading, Spacer, useColorMode, IconButton } from '@chakra-ui/react'
import { Link as RouterLink } from 'react-router-dom'
import { MoonIcon, SunIcon } from '@chakra-ui/icons'

const Navbar = () => {
  const { colorMode, toggleColorMode } = useColorMode()

  return (
    <Box as="nav" bg="brand.500" color="white" px={4} py={3} shadow="md">
      <Flex align="center" maxW="1200px" mx="auto">
        <Heading as="h1" size="md">
          <RouterLink to="/">Seraphy</RouterLink>
        </Heading>
        
        <Spacer />
        
        <Flex gap={4}>
          <Button as={RouterLink} to="/dashboard" variant="ghost" colorScheme="whiteAlpha">
            Dashboard
          </Button>
          <Button as={RouterLink} to="/" variant="ghost" colorScheme="whiteAlpha">
            New Document
          </Button>
          <IconButton
            icon={colorMode === 'light' ? <MoonIcon /> : <SunIcon />}
            onClick={toggleColorMode}
            variant="ghost"
            colorScheme="whiteAlpha"
            aria-label="Toggle color mode"
          />
        </Flex>
      </Flex>
    </Box>
  )
}

export default Navbar
