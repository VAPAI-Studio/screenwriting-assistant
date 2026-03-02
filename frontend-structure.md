# Frontend Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── Layout/
│   │   │   ├── Layout.tsx
│   │   │   ├── Header.tsx
│   │   │   └── Sidebar.tsx
│   │   ├── Projects/
│   │   │   ├── ProjectList.tsx
│   │   │   ├── ProjectCard.tsx
│   │   │   └── CreateProjectModal.tsx
│   │   ├── Editor/
│   │   │   ├── Editor.tsx
│   │   │   ├── SectionEditor.tsx
│   │   │   ├── Checklist.tsx
│   │   │   └── ReviewPanel.tsx
│   │   └── UI/
│   │       ├── Button.tsx
│   │       ├── Input.tsx
│   │       ├── Modal.tsx
│   │       └── Card.tsx
│   ├── hooks/
│   │   ├── useProjects.ts
│   │   ├── useSections.ts
│   │   └── useKeyboardShortcuts.ts
│   ├── lib/
│   │   ├── api.ts
│   │   └── constants.ts
│   ├── types/
│   │   └── index.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── .env.example
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```
