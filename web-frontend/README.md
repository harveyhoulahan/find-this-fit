# Find This Fit - Web Frontend

This is the web landing page for Find This Fit, built with Next.js, TypeScript, and Tailwind CSS.

## Getting Started

1. Install dependencies:
```bash
npm install
```

2. Add missing utility dependencies:
```bash
npm install clsx tailwind-merge
```

3. Run the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

- `/app` - Next.js app directory with pages and layouts
- `/components/ui` - Reusable UI components (shadcn-based)
- `/lib` - Utility functions

## Features

- 🎨 Modern UI with Framer Motion animations
- 📱 Fully responsive design
- 🎯 shadcn/ui component library
- ⚡ Fast development with Hot Module Replacement

## Backend Integration

The backend API runs on `http://localhost:8000`. Make sure Docker containers are running:

```bash
cd ..
docker-compose up -d
```
