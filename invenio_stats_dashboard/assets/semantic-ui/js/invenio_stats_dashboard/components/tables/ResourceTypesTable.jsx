const getChartOption = () => {
  const chartData = rows.map(([_, label, count, id]) => ({
    name: label,
    value: parseInt(count.replace(/,/g, '')),
    id: id
  }));

  return {
    grid: {
      top: '10%',
      right: '5%',
      bottom: '10%',
      left: '5%',
      containLabel: true
    },
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    series: [
      {
        type: 'pie',
        radius: '50%',
        data: chartData,
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  };
};