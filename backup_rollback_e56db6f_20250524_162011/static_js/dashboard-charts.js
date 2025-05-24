// static/js/cotisations/dashboard-charts.js

/**
 * Initialise les graphiques du tableau de bord des cotisations
 */
class DashboardCharts {
    /**
     * Constructeur
     */
    constructor() {
        this.charts = {};
        this.initCharts();
    }

    /**
     * Initialise tous les graphiques
     */
    initCharts() {
        this.initEvolutionChart();
        this.initStatutsChart();
        this.initTypeMembreChart();
    }

    /**
     * Récupère et nettoie les données pour les graphiques
     * @param {string} dataId - ID de l'élément contenant les données
     * @returns {Array} - Données nettoyées
     */
    getSafeData(dataId) {
        const element = document.getElementById(dataId);
        if (!element) {
            console.error(`Élément avec ID '${dataId}' non trouvé`);
            return [];
        }
        
        try {
            // Récupérer les données et les nettoyer
            const rawData = element.textContent.trim();
            if (!rawData) {
                console.warn(`Données vides pour '${dataId}'`);
                return [];
            }
            
            // Log pour le débogage
            console.debug(`Données brutes pour ${dataId}:`, rawData.substring(0, 100) + (rawData.length > 100 ? '...' : ''));
            
            // Valider que c'est du JSON valide
            const parsedData = JSON.parse(rawData);
            return parsedData || [];
        } catch (e) {
            console.error(`Erreur lors du parsing des données ${dataId}:`, e);
            // Afficher les 50 premiers caractères pour le débogage
            console.error(`Début des données: "${element.textContent.substring(0, 50)}..."`);
            return [];
        }
    }

    /**
     * Initialise le graphique d'évolution des cotisations
     */
    initEvolutionChart() {
        const chartElement = document.getElementById('cotisationsChart');
        if (!chartElement) return;

        // Récupérer les données de manière sécurisée
        const cotisationsData = this.getSafeData('cotisations-data');
        const paiementsData = this.getSafeData('paiements-data');
        const nonPayeesData = this.getSafeData('non-payees-data');

        // Créer le graphique
        this.charts.evolution = new Chart(chartElement, {
            type: 'bar',
            data: {
                labels: cotisationsData.map(item => item.month),
                datasets: [
                    {
                        label: 'Cotisations émises',
                        data: cotisationsData.map(item => item.total),
                        backgroundColor: 'rgba(54, 162, 235, 0.7)',
                    },
                    {
                        label: 'Paiements reçus',
                        data: paiementsData.map(item => item.total),
                        backgroundColor: 'rgba(75, 192, 192, 0.7)',
                    },
                    {
                        label: 'Cotisations non payées',
                        data: nonPayeesData.map(item => item.total),
                        backgroundColor: 'rgba(255, 99, 132, 0.7)',
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: false,
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value + ' €';
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Initialise le graphique des statuts de paiement
     */
    initStatutsChart() {
        const chartElement = document.getElementById('statutsChart');
        if (!chartElement) return;

        // Récupérer les données de statut
        const statutsData = this.getSafeData('statuts-data');
        
        // Données pour le graphique
        const data = {
            labels: ['Non payée', 'Partiellement payée', 'Payée'],
            datasets: [{
                data: [
                    statutsData.non_payee || 0,
                    statutsData.partiellement_payee || 0,
                    statutsData.payee || 0
                ],
                backgroundColor: [
                    'rgba(255, 99, 132, 0.7)',
                    'rgba(255, 205, 86, 0.7)',
                    'rgba(75, 192, 192, 0.7)'
                ]
            }]
        };

        // Créer le graphique
        this.charts.statuts = new Chart(chartElement, {
            type: 'doughnut',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                    }
                }
            }
        });
    }

    /**
     * Initialise le graphique par type de membre
     */
    initTypeMembreChart() {
        const chartElement = document.getElementById('typeMembreChart');
        if (!chartElement) return;

        try {
            // Récupérer les données des types de membre
            const typesData = this.getSafeData('types-data');
            
            // Vérification supplémentaire des données
            if (!typesData || !Array.isArray(typesData) || typesData.length === 0) {
                console.warn("Aucune donnée trouvée pour les types de membre");
                
                // Afficher un message dans le canvas
                const ctx = chartElement.getContext('2d');
                ctx.font = '14px Arial';
                ctx.fillStyle = '#666';
                ctx.textAlign = 'center';
                ctx.fillText('Aucune donnée disponible', chartElement.width / 2, chartElement.height / 2);
                return;
            }
            
            // Couleurs pour le graphique
            const backgroundColors = [
                'rgba(78, 115, 223, 0.7)',
                'rgba(28, 200, 138, 0.7)',
                'rgba(246, 194, 62, 0.7)',
                'rgba(231, 74, 59, 0.7)',
                'rgba(54, 185, 204, 0.7)',
                'rgba(133, 135, 150, 0.7)'
            ];

            // Créer le graphique
            this.charts.typeMembre = new Chart(chartElement, {
                type: 'doughnut',
                data: {
                    labels: typesData.map(item => item.libelle),
                    datasets: [{
                        data: typesData.map(item => item.total),
                        backgroundColor: backgroundColors.slice(0, typesData.length)
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    let label = context.label || '';
                                    let value = context.raw || 0;
                                    return label + ': ' + value.toFixed(2) + ' €';
                                }
                            }
                        }
                    }
                }
            });
        } catch (e) {
            console.error("Erreur lors de la création du graphique des types de membre:", e);
        }
    }
}

// Initialiser les graphiques au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    // Vérifier que Chart.js est chargé
    if (typeof Chart !== 'undefined') {
        new DashboardCharts();
    } else {
        console.error('Chart.js n\'est pas chargé.');
    }
});