document.getElementById("run").onclick = async () => {
  const jobDesc = document.getElementById("jobDesc").value;
  const output = document.getElementById("output");

  output.textContent = "Generating...";

  const res = await fetch("http://127.0.0.1:8000/agent/fill_packet", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      job_description: jobDesc
    })
  });

  const data = await res.json();
  output.textContent = JSON.stringify(data, null, 2);
};
