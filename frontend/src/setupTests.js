// Fix for TextEncoder not defined in jsdom/node
if (typeof global.TextEncoder === 'undefined') {
	const { TextEncoder } = require('util');
	global.TextEncoder = TextEncoder;
}
// setupTests.js
import '@testing-library/jest-dom';

// Suppress console output in tests
beforeAll(() => {
	jest.spyOn(console, 'error').mockImplementation(() => {});
	jest.spyOn(console, 'warn').mockImplementation(() => {});
	jest.spyOn(console, 'log').mockImplementation(() => {});
});
