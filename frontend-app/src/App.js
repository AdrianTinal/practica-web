// App.js

import './App.css';
import React, { useState, useEffect } from "react";

function App() {
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const [resultado, setResultado] = useState(null);
  const [historial, setHistorial] = useState([]);
  

  const [filterType, setFilterType] = useState("");
  const [orderBy, setOrderBy] = useState("date");
  const [orderDirection, setOrderDirection] = useState("desc");

  const handleOperation = async (operation) => {
    try {
      const res = await fetch(`/calculadora/${operation}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ a: parseFloat(a), b: parseFloat(b) })
      });
      
      if (res.status !== 200) {
        const data = await res.json();
        alert(`Error: ${data.detail}`);
        return;
      }

      const data = await res.json();
      setResultado(data.resultado);
      obtenerHistorial();
    } catch (error) {
      console.error("Error al realizar la operación:", error);
    }
  };

  const sumar = () => handleOperation("sum");
  const restar = () => handleOperation("resta");
  const multiplicar = () => handleOperation("mult");
  const dividir = () => handleOperation("div");

  const obtenerHistorial = async () => {
    try {

      const res = await fetch("/calculadora/historial", {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          operacion: filterType || null,
          order_by: orderBy,
          order_direction: orderDirection
        })
      });
      
      if (res.status !== 200) {
        const data = await res.json();
        alert(`Error: ${data.detail}`);
        return;
      }

      const data = await res.json();
      setHistorial(data.historial);
    } catch (error) {
      console.error("Error al obtener el historial:", error);
    }
  };

  useEffect(() => {
    obtenerHistorial();
  }, [filterType, orderBy, orderDirection]); 

  return (
    <div>
      <div className="calculator-container">
        <h1>Calculadora</h1>
        <div className="display">
          {resultado !== null ? resultado : "0"}
        </div>
        <input
          type="number"
          value={a}
          onChange={(e) => setA(e.target.value)}
          placeholder="Número 1"
        />
        <input
          type="number"
          value={b}
          onChange={(e) => setB(e.target.value)}
          placeholder="Número 2"
        />
        <div className="button-grid">
          <button className="operation" onClick={sumar}>+</button>
          <button className="operation" onClick={restar}>-</button>
          <button className="operation" onClick={multiplicar}>x</button>
          <button className="operation" onClick={dividir}>/</button>
        </div>
      </div>
      

      <div className="history-container">
        <h3>Historial:</h3>
        <div className="filter-controls">
          <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
            <option value="">Todas las operaciones</option>
            <option value="sum">Suma</option>
            <option value="resta">Resta</option>
            <option value="mult">Multiplicación</option>
            <option value="div">División</option>
          </select>
          <select value={orderBy} onChange={(e) => setOrderBy(e.target.value)}>
            <option value="date">Ordenar por Fecha</option>
            <option value="resultado">Ordenar por Resultado</option>
          </select>
          <select value={orderDirection} onChange={(e) => setOrderDirection(e.target.value)}>
            <option value="desc">Descendente</option>
            <option value="asc">Ascendente</option>
          </select>
        </div>
        <ul>
          {historial.map((op, i) => (
            <li key={i}>
              {op.a} {op.operacion === "sum" ? "+" : ""}
              {op.operacion === "resta" ? "-" : ""}
              {op.operacion === "mult" ? "x" : ""}
              {op.operacion === "div" ? "/" : ""}
              {op.b} = {op.resultado} ({new Date(op.date).toLocaleDateString()})
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default App;