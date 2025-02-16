let resultsChart = null;

function updateChart(data) {
    const ctx = document.getElementById('resultsChart').getContext('2d');
    
    const labels = Object.keys(data).map(party => 
        party.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
    );
    
    const values = Object.values(data).map(info => info.agreement);
    
    const chartData = {
        labels: labels,
        datasets: [{
            label: 'Agreement Percentage',
            data: values,
            backgroundColor: [
                'rgba(54, 162, 235, 0.5)',  // Democratic
                'rgba(255, 99, 132, 0.5)',  // Republican
                'rgba(75, 192, 192, 0.5)',  // Green
                'rgba(255, 206, 86, 0.5)',  // Libertarian
                'rgba(153, 102, 255, 0.5)', // Independent
            ],
            borderColor: [
                'rgba(54, 162, 235, 1)',
                'rgba(255, 99, 132, 1)',
                'rgba(75, 192, 192, 1)',
                'rgba(255, 206, 86, 1)',
                'rgba(153, 102, 255, 1)',
            ],
            borderWidth: 1
        }]
    };

    const options = {
        responsive: true,
        scales: {
            y: {
                beginAtZero: true,
                max: 100,
                ticks: {
                    callback: function(value) {
                        return value + '%';
                    }
                }
            }
        },
        plugins: {
            legend: {
                display: true,
                position: 'bottom'
            }
        }
    };

    if (resultsChart) {
        resultsChart.destroy();
    }

    resultsChart = new Chart(ctx, {
        type: 'bar',
        data: chartData,
        options: options
    });
}
