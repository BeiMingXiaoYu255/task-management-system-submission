/** 前端应用入口：挂载根组件并加载全局样式。 */

import React from 'react'
import ReactDOM from 'react-dom/client'

import App from './App'
import './styles/tokens.css'
import './styles/global.css'

/** 根节点：不存在时抛出明确错误，便于定位 index.html 问题。 */
const rootElement = document.getElementById('root')
if (rootElement === null) {
  throw new Error('Root element #root was not found')
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
