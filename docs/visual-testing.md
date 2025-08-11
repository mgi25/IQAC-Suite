# Visual Testing

To run visual regression tests locally with Percy, first set your project token:

```bash
export PERCY_TOKEN="<your-token>"
```

Then execute the Playwright tests through Percy:

```bash
npx percy exec -- playwright test
```

This command wraps `playwright test` so that snapshots are uploaded to Percy.
