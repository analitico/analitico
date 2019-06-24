"use strict";

// Constants
const PORT = 8080;
const HOST = "0.0.0.0";
const configurationUrl = "./config.json";
const slacWebhookUri = "";

const express = require("express");
const cron = require("node-cron");
const fs = require("fs");
const request = require("request");
const Validator = require("jsonschema").Validator;
const validator = new Validator();
const Slack = require("slack-node");

const slack = new Slack();
slack.setWebhook(slacWebhookUri);

let monitoringTasks = [];
let monitoringTasksDict = {};
// App
const app = express();
// Health check
app.get("/", (req, res) => {
    res.send("Up and running");
});

app.listen(PORT, HOST);


/**
 * Get monitoring configuration
 */
function getConfiguration() {
    // load from file
    return new Promise((resolve, reject) => {
        fs.readFile(configurationUrl, function (err, contents) {
            if (err) {
                return reject(err);
            }
            try {
                // parse
                const parsed = JSON.parse(contents);
                resolve(parsed);
            }
            catch (err) {
                return reject(err);
            }
        })
    })
}

function destroyAllTasks() {
    monitoringTasks.forEach(task => {
        task.destroy();
    });
    monitoringTasks = [];
    monitoringTasksDict = {};
}

function getCronFunction(taskConfig) {
    return () => {
        const name = taskConfig.name;
        const url = taskConfig.url;
        const method = taskConfig.method || "GET";
        const data = taskConfig.data;
        const authorization = taskConfig.authorization;
        const schema = taskConfig.schema;
        const requestMaxTime = taskConfig.requestMaxTime || 5000;
        const payload = {
            method: method,
            uri: url,
            time: true
        };
        if (method === "POST") {
            payload.json = data;
        }
        if (authorization && authorization.bearerToken) {
            payload.auth = {
                "bearer": authorization.bearerToken
            };
        }
        try {
            request(payload, function (error, response, body) {
                try {
                    if (error) {
                        throw error;
                    }

                    if (response.elapsedTime > requestMaxTime) {
                        notifyOnSlack(`${name}: exceeded max time ${response.elapsedTime}ms (max time: ${requestMaxTime}ms)`);
                    }

                    const result = validator.validate(body, schema);
                    if (!result.valid) {
                        const errors = result.errors;
                        notifyOnSlack(`${name}: ${errors}`);
                    }
                    else {
                        console.log(`${name}: ok`)
                    }
                }
                catch (error) {
                    notifyOnSlack(`${name}: ${error}`);
                }
            })
        }
        catch (error) {
                notifyOnSlack(`${name}: request errror ${error}`);
            }
        }
}

    function setupMonitoring() {
        getConfiguration()
            .then((configuration) => {
                // destroy all current tasks
                destroyAllTasks();
                // for each configuration, create a cron
                const tasks = configuration.tasks;
                console.log(`Configuring ${tasks.length} tasks...`);
                tasks.forEach(taskConfig => {
                    const name = taskConfig.name;
                    const schedule = taskConfig.schedule;


                    if (monitoringTasksDict[name]) {
                        console.error("Duplicate name");
                        return true;
                    }
                    if (!cron.validate(schedule)) {
                        console.error(`Invalid schedule ${schedule}`);
                        return true;
                    }
                    const cronFunction = getCronFunction(taskConfig);
                    cronFunction();
                    const task = cron.schedule(schedule, cronFunction, { scheduled: true });
                    monitoringTasks.push(task);
                    monitoringTasksDict[name] = task;
                });
            })
            .catch((e) => {
                return console.error(e);
            })
    }

    /**
     * Send a slack notification
     * @param {*} message 
     */
    function notifyOnSlack(message) {
        return console.error(message);
        slack.webhook({
            channel: "#pingdom",
            username: "monitor",
            text: message
        });
    }

    // setup monitors
    setupMonitoring();