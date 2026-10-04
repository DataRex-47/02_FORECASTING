-- Entrada de la ejecucion: 15 dias reales + 8 dias a predecir
-- Ejemplo: predecir del 24 al 31 de diciembre de 2015 (historia real: del 9 al 23)
-- Plantilla: ventas_diarias es la tabla de ventas en formato largo (fecha, tienda, producto, ventas)
WITH ventana AS (                 -- calendario de los 23 dias: se conoce por adelantado
    SELECT date, wm_yr_wk, weekday, month, event_name_1, event_type_1
    FROM calendar
    WHERE date BETWEEN '2015-12-09' AND '2015-12-31'
),
series AS (                       -- las 20 series: 10 productos en CA_3 y 10 en CA_4
    SELECT DISTINCT store_id, item_id FROM ventas_diarias
),
esqueleto AS (                    -- cada dia por cada serie (asi existen tambien los dias futuros)
    SELECT v.*, s.store_id, s.item_id
    FROM ventana v CROSS JOIN series s
),
ultimo_precio AS (                -- alternativa 2: ultimo precio valido hasta el corte
    SELECT p.store_id, p.item_id, p.sell_price
    FROM sell_prices p
    WHERE p.wm_yr_wk = (SELECT MAX(p2.wm_yr_wk) FROM sell_prices p2
                        WHERE p2.store_id = p.store_id AND p2.item_id = p.item_id
                          AND p2.wm_yr_wk <= (SELECT wm_yr_wk FROM calendar WHERE date = '2015-12-23'))
)
SELECT e.date, e.store_id, e.item_id,
       CASE WHEN e.date <= '2015-12-23' THEN d.ventas ELSE 0 END AS ventas,   -- futuro en 0: lo sobrescribe el recursivo
       COALESCE(p.sell_price, u.sell_price) AS sell_price,                    -- precio planificado (promos) o ultimo valido
       e.month, e.weekday, e.event_name_1, e.event_type_1                     -- eventos: NULL si no hay (no 0)
FROM esqueleto e
LEFT JOIN ventas_diarias d ON d.date = e.date AND d.store_id = e.store_id AND d.item_id = e.item_id
LEFT JOIN sell_prices p ON p.wm_yr_wk = e.wm_yr_wk AND p.store_id = e.store_id AND p.item_id = e.item_id
LEFT JOIN ultimo_precio u ON u.store_id = e.store_id AND u.item_id = e.item_id
ORDER BY e.date, e.store_id, e.item_id;
