import '@testing-library/jest-dom';

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock echarts-for-react globally
jest.mock('echarts-for-react', () => {
  const React = require('react');
  const mockChartInstance = {
    resize: jest.fn(),
    setOption: jest.fn(),
    getOption: jest.fn(),
    dispose: jest.fn(),
  };

  return React.forwardRef(function MockReactECharts({ option, onChartReady, ...props }, ref) {
    // Expose getEchartsInstance method on the ref
    React.useImperativeHandle(ref, () => ({
      getEchartsInstance: () => mockChartInstance,
    }));

    // Call onChartReady if provided with a mock chart instance
    React.useEffect(() => {
      if (onChartReady) {
        setTimeout(() => {
          onChartReady(mockChartInstance);
        }, 0);
      }
    }, [onChartReady]);

    return (
      <div data-testid="mock-echarts" {...props}>
        <div data-testid="chart-option" data-option={JSON.stringify(option)} />
      </div>
    );
  });
});
