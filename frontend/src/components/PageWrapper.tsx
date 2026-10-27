import { motion } from 'framer-motion'

interface Props {
  children: React.ReactNode
  className?: string
}

export default function PageWrapper({ children, className = '' }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ duration: 0.25 }}
      className={`flex flex-col gap-6 ${className}`}
    >
      {children}
    </motion.div>
  )
}
