/** 404 页面：路径不存在时的兜底展示。 */

import { Link } from 'react-router-dom'

/** 404 页面。 */
export default function NotFoundPage() {
  return (
    <div className="page-container">
      <h1>Page not found</h1>
      <p>The page you are looking for may have been moved or deleted.</p>
      <Link to="/dashboard">Back to Dashboard</Link>
    </div>
  )
}
