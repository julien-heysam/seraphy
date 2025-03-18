import { Box, Text, Flex, Link } from '@chakra-ui/react'

const Footer = () => {
  return (
    <Box as="footer" bg="gray.100" _dark={{ bg: "gray.900" }} py={4}>
      <Flex 
        direction={{ base: "column", md: "row" }} 
        maxW="1200px" 
        mx="auto"
        px={4}
        align="center"
        justify="space-between"
      >
        <Text fontSize="sm">
          &copy; {new Date().getFullYear()} Seraphy. All rights reserved.
        </Text>
        <Flex gap={4} mt={{ base: 2, md: 0 }}>
          <Link href="#" fontSize="sm">Privacy Policy</Link>
          <Link href="#" fontSize="sm">Terms of Service</Link>
          <Link href="#" fontSize="sm">Contact</Link>
        </Flex>
      </Flex>
    </Box>
  )
}

export default Footer
