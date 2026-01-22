# Frontend Troubleshooting Guide

## Vite Exits Immediately

If `npm run dev` starts and then immediately returns to the prompt, try these steps:

### 1. Check for Errors

Run with verbose output:
```powershell
npm run dev -- --debug
```

Or check the full output:
```powershell
npm run dev 2>&1 | Out-File -FilePath vite-output.txt
```

### 2. Check Port Availability

Port 5173 might be in use. Check with:
```powershell
netstat -ano | findstr :5173
```

If the port is in use, either:
- Stop the process using that port
- Change the port in `vite.config.ts`:
  ```typescript
  server: {
    port: 5174,  // Change this
  }
  ```

### 3. Clear Cache and Reinstall

```powershell
# Remove node_modules and lock file
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json

# Reinstall
npm install

# Try again
npm run dev
```

### 4. Check Node.js Version

Vite 7 requires Node.js 18+. Check your version:
```powershell
node --version
```

If it's too old, update Node.js from https://nodejs.org/

### 5. Check for TypeScript Errors

```powershell
npm run check
```

### 6. Try Running Vite Directly

```powershell
npx vite
```

### 7. Check Windows Firewall

Windows Firewall might be blocking Vite. Try running PowerShell as Administrator.

## Common Error Messages

### "Cannot find module"
- Run `npm install` again
- Delete `node_modules` and `package-lock.json`, then `npm install`

### "Port already in use"
- Change port in `vite.config.ts`
- Or kill the process: `taskkill /PID <process_id> /F`

### "EADDRINUSE"
- Same as above - port conflict

### "SyntaxError" or TypeScript errors
- Run `npm run check` to see TypeScript errors
- Fix any type errors in the code

## Getting Help

If none of these work, share:
1. Full error output from `npm run dev`
2. Node.js version: `node --version`
3. npm version: `npm --version`
4. Output of `npm run check`
