document.addEventListener('DOMContentLoaded', function() {
        const amountInput = document.getElementById('id_amount');
        const rateInput = document.getElementById('id_rate_at_moment');
        const resultSpan = document.getElementById('calc-result');
        
        const accountSelect = document.getElementById('id_account');
        const dateInput = document.querySelector('input[type="date"]');
        const cbrRateDisplay = document.getElementById('cbr-rate-display');
        const currencyDisplay = document.getElementById('selected-currency-display');

        const currenciesData = JSON.parse(document.getElementById('currencies-data').textContent);

        function calculateTotal() {
            const amount = parseFloat(amountInput.value) || 0;
            const manualRate = parseFloat(rateInput.value) || 0;
            let finalRate = manualRate;

            if (finalRate === 0 && cbrRateDisplay.dataset.rate) {
                finalRate = parseFloat(cbrRateDisplay.dataset.rate) || 0;
            }

            resultSpan.textContent = (amount * finalRate).toFixed(2);
        }

        function updateCurrencyDisplay() {
            const selectedOption = accountSelect.options[accountSelect.selectedIndex];
            const match = selectedOption.text.match(/\(([^)]+)\)/);
            const currencyCode = match ? match[1] : '—';
            if (currencyDisplay) {
                currencyDisplay.textContent = currencyCode;
            }
            return currencyCode;
        }

        function fetchCbrRate() {
            const currencyCode = updateCurrencyDisplay();
            const cbrId = currenciesData[currencyCode]?.cbr_id;
            const dateVal = dateInput.value;

            if (cbrId && dateVal) {
                cbrRateDisplay.textContent = 'Загрузка...';
                
                fetch(`/api/get-rate/?date=${dateVal}&cbr_id=${cbrId}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.rate) {
                            cbrRateDisplay.textContent = parseFloat(data.rate).toFixed(4) + ' ₽';
                            cbrRateDisplay.dataset.rate = data.rate;
                        } else {
                            cbrRateDisplay.textContent = 'Нет данных';
                            delete cbrRateDisplay.dataset.rate;
                        }
                        calculateTotal();
                    })
                    .catch(err => {
                        cbrRateDisplay.textContent = 'Ошибка API';
                        delete cbrRateDisplay.dataset.rate;
                        calculateTotal();
                    });
            }
            
        }

        amountInput.addEventListener('input', calculateTotal);
        rateInput.addEventListener('input', calculateTotal);
        accountSelect.addEventListener('change', fetchCbrRate);
        dateInput.addEventListener('change', fetchCbrRate);

        fetchCbrRate();
    });