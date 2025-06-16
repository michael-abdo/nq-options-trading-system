#!/usr/bin/env node
/**
 * Dashboard Screenshot Tool
 * Takes a screenshot of the running dashboard for debugging
 */

const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

async function takeScreenshot() {
    const browser = await puppeteer.launch({
        headless: true,
        defaultViewport: {
            width: 1920,
            height: 1080
        }
    });

    try {
        const page = await browser.newPage();

        // Navigate to dashboard
        console.log('📷 Navigating to dashboard...');
        await page.goto('http://127.0.0.1:8050/', {
            waitUntil: 'networkidle2',
            timeout: 30000
        });

        // Wait for chart to load
        console.log('⏳ Waiting for chart to render...');
        await page.waitForTimeout(5000);

        // Create screenshots directory if it doesn't exist
        const screenshotDir = '/Users/Mike/trading/algos/EOD/tests/screenshots';
        if (!fs.existsSync(screenshotDir)) {
            fs.mkdirSync(screenshotDir, { recursive: true });
        }

        // Take screenshot
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const filename = path.join(screenshotDir, `dashboard_${timestamp}.png`);

        await page.screenshot({
            path: filename,
            fullPage: true
        });

        console.log(`✅ Screenshot saved: ${filename}`);

        // Also save a specific "latest" version for easy access
        const latestPath = path.join(screenshotDir, 'dashboard_latest.png');
        await page.screenshot({
            path: latestPath,
            fullPage: true
        });

        console.log(`✅ Latest screenshot: ${latestPath}`);

    } catch (error) {
        console.error('❌ Screenshot failed:', error);
    } finally {
        await browser.close();
    }
}

// Run the screenshot
takeScreenshot();
