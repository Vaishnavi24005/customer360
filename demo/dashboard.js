'use strict';
const data = window.C360;
const get = id => document.getElementById(id);
const number = new Intl.NumberFormat('en-US');
const dollars = new Intl.NumberFormat('en-US', {style:'currency', currency:'USD', maximumFractionDigits:0});
const percent = new Intl.NumberFormat('en-US', {style:'percent', maximumFractionDigits:0});
const format = (value, formatter) => value == null ? '—' : formatter.format(value);

function row(body, values) {
    const tr = body.insertRow();
    for (const value of values) tr.insertCell().textContent = value;
}

get('provenance').textContent = data.provenance;
for (const name of ['sessions', 'orders', 'customer_profile']) {
    get(name).textContent = number.format(data.counts[name]);
}

const model = get('model');
for (const name of ['First touch', 'Last touch', 'Linear', 'Time decay']) {
    model.add(new Option(name, name));
}
model.value = 'Time decay';

function render() {
    const campaigns = data.campaign_performance.filter(row => row.model === model.value);
    campaigns.sort((a,b) => b.credited_revenue - a.credited_revenue);
    const byChannel = new Map();
    get('campaigns').replaceChildren();
    for (const item of campaigns) {
        row(get('campaigns'), [
            item.channel + (item.campaign === '(unassigned)' ? '' : ' / ' + item.campaign),
            format(item.credited_revenue, dollars), format(item.spend, dollars),
            item.roas == null ? '—' : Number(item.roas).toFixed(2) + '×',
            format(item.roi, percent), format(item.cpa, dollars),
        ]);
        byChannel.set(item.channel, (byChannel.get(item.channel) || 0) + Number(item.credited_revenue));
    }
    get('revenue').textContent = dollars.format([...byChannel.values()].reduce((a,b) => a+b, 0));
    const chart = get('channels');
    chart.replaceChildren();
    const max = Math.max(1, ...byChannel.values());
    for (const [name, revenue] of [...byChannel].sort((a,b) => b[1]-a[1])) {
        const bar = document.createElement('div');
        bar.className = 'bar';
        const label = document.createElement('span');
        label.textContent = name;
        const meter = document.createElement('meter');
        meter.max = max;
        meter.value = revenue;
        meter.setAttribute('aria-label', name + ' credited revenue');
        const value = document.createElement('span');
        value.textContent = dollars.format(revenue);
        bar.append(label, meter, value);
        chart.append(bar);
    }
}
model.addEventListener('change', render);
for (const item of data.segments) {
    row(get('segments'), [item.segment, number.format(item.customers), format(item.avg_annualized_ltv, dollars)]);
}
render();
